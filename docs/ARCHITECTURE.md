# Architecture

## Layered overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  Browser (Next.js 15, React 19, shadcn/ui, Recharts, Framer Motion)  │
└────────────────────────┬─────────────────────────────────────────────┘
                         │ REST (CRUD, queries)  +  WS (1Hz tick feed)
┌────────────────────────┴─────────────────────────────────────────────┐
│  FastAPI gateway (apps/api/arena)                                    │
│  • routes/          thin HTTP handlers, Pydantic schemas             │
│  • ws/hub.py        single-broadcaster WebSocket fanout              │
│  • services/        domain logic (energy_sim, allocator, …)          │
│  • repositories/    persistence boundary (async SQLAlchemy)          │
│  • core/            db, redis, logging, settings                     │
└──────────┬─────────────────────────────────────────┬─────────────────┘
           │                                         │
   ┌───────┴───────┐                          ┌──────┴──────┐
   │  PostgreSQL   │                          │    Redis    │
   │  (Prisma DDL) │                          │  pub/sub +  │
   │  time-series  │                          │  queues     │
   └───────────────┘                          └─────────────┘
```

## Module boundaries

| Module | Responsibility |
|---|---|
| `arena.routes.*` | HTTP surface; no business logic |
| `arena.services.*` | Domain logic; pure functions where possible, otherwise stateful only via `core` |
| `arena.repositories.*` | All DB I/O — services never touch the session directly |
| `arena.ws.hub` | One in-process broadcaster, fanout via `asyncio.Queue` per subscriber |
| `arena.core.*` | Engine glue: `db.py` (SQLAlchemy engine), `redis.py`, `logging.py`, `config.py` |

## Realtime loop

The simulation engine is one `asyncio` task launched at app startup
(`arena.main:lifespan`). Each tick:

1. Reads node fleet + open workloads from the in-memory state cache.
2. Calls `energy_sim.advance()` to step generation models per region.
3. Calls `allocator.allocate(surplus_kwh)` to drain the priority queue.
4. Calls `mining_sim.tick()` for any running mining workloads.
5. Computes carbon + utilization scores.
6. Persists the tick (`repositories.energy.insert_tick`).
7. Broadcasts a `TickEvent` over the WS hub.

The cache is the source of truth between ticks; Postgres is the durable
write-ahead log for analytics. Redis fronts the workload **submission**
queue so an external API client can enqueue without holding a DB connection.

## Why FastAPI + asyncio (vs. Go)

We considered Go + Gin for the simulation engine. Tradeoff:

- **Go pros:** lower per-tick latency, easier to run many sim shards.
- **FastAPI pros:** Pydantic schema reuse with OpenAPI clients, ergonomic
  async, faster vertical-slice time to demo, easier to splice ML forecasters
  (sklearn / numpy already in the runtime).

For a single-region 1Hz sim with ~thousands of nodes, FastAPI is bounded by
the broadcaster, not the language. The simulation engine is structured so
each tick is a pure transform `(state, surplus) -> (state', events)` — it
can be re-hosted in Go behind the same WS contract if/when needed.

## Why Prisma DDL + SQLAlchemy runtime

- Prisma schema is the **single declarative source of truth** for the data
  model — easy to read, easy to diff in PRs, easy to generate ER diagrams.
- SQLAlchemy 2.0 async is the **runtime client** — best-in-class async
  support inside FastAPI, mature migrations via Alembic.

This split is uncommon but deliberate: design-first in Prisma, runtime in
SQLAlchemy. See `apps/api/prisma/schema.prisma` for the canonical schema and
`apps/api/arena/models.py` for the runtime mirror. The two are kept in sync
manually; in production we'd add a generator.

## Folder layout

```
apps/
  api/
    arena/
      main.py              FastAPI app + lifespan + sim task
      config.py            pydantic-settings, env-driven
      models.py            SQLAlchemy ORM mirror of prisma/schema.prisma
      schemas/             Pydantic DTOs (one file per domain)
      routes/              HTTP endpoints
      services/            domain logic
      repositories/        DB access
      ws/                  WebSocket hub
      core/                db / redis / logging
      seed.py              demo seed
    prisma/
      schema.prisma        canonical schema
    tests/                 pytest
    Dockerfile
    pyproject.toml
    requirements.txt
  web/
    app/                   Next.js 15 App Router
      (dashboard)/         route group for app shell
        page.tsx           "/" → energy dashboard
        compute/page.tsx
        nodes/page.tsx
        blockchain/page.tsx
        analytics/page.tsx
        ai/page.tsx
      layout.tsx
      globals.css
    components/
      ui/                  shadcn primitives
      charts/              recharts wrappers
      dashboard/           composed widgets
      shell/               sidebar / topbar
    lib/                   api client, ws client, utils
    hooks/                 useTick, useApi
    types/                 shared TS types (mirrors backend DTOs)
    public/
docs/
  ARCHITECTURE.md
  SYSTEM_DESIGN.md
  API.md
scripts/
docker-compose.yml
```
