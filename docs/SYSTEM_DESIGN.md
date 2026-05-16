# System Design

## Problem

Renewable energy is **non-dispatchable**: solar peaks at noon, wind peaks
overnight, and demand follows a different curve entirely. When generation
exceeds demand and storage is saturated, ISOs instruct wind/solar farms to
**curtail** — i.e., spill clean energy. Curtailment is rising as renewable
penetration grows.

Compute is the inverse problem: large-scale AI training, distributed
science, and mining are **dispatchable** loads — they can run when and where
energy is cheap. The matching problem is real-time and global.

ARENA-GRID models the matching loop in a single tractable system.

## Goals

1. **Demonstrably realtime** — sub-second tick-to-screen.
2. **Production-shaped** — service/repository layering, typed contracts,
   migrations, healthchecks.
3. **Composable** — sim engine, allocator, and forecaster can each be
   replaced independently (Strategy pattern).
4. **Honest fidelity** — the energy and allocator models are simplified but
   not toys; the numbers feel right within an order of magnitude.

## Non-goals

- Real ISO market integration (future work).
- Settlement / accounting correctness (this is a sim).
- Multi-tenant isolation.

## Key decisions and tradeoffs

### 1. Single in-process simulation task

The sim loop is one `asyncio` task in the API process. We considered a
separate worker (Celery / RQ / arq).

**Why one process now:** the sim is ~ms per tick, fits in memory, and the
broadcaster needs in-process state anyway. Splitting adds operational
complexity for no current win.

**When to split:** when (a) we want horizontal sim sharding by region, or
(b) we want the sim to outlive API restarts. Path: extract `arena.services.engine`
behind a Redis-streams contract — services already speak that protocol for
workload submissions.

### 2. WebSocket fanout via a single broadcaster, not Redis pub/sub to browsers

Browsers connect to FastAPI; FastAPI does the fanout. We do **not** put the
browser on a Redis subscription directly — that requires Redis-over-WS or a
proxy and complicates auth.

**Cost:** the API node is the fanout bottleneck. At ~1000 concurrent viewers
on a 1Hz tick with a 4KB payload, that's 4 MB/s per node — well within a
single uvicorn worker. Past that, scale out and front with a sticky LB; the
WS hub is stateless apart from its subscriber set.

### 3. Postgres for time-series, not a TSDB

We store ticks as rows in `energy_ticks`. We considered TimescaleDB and
ClickHouse.

**Why Postgres:** one less moving piece, BRIN indexes on the timestamp
column give us range scans that are fast enough at MVP scale, and the
analytics dashboards query aggregated buckets, not raw points.

**When to switch:** once we retain >30 days of 1Hz ticks per node-region
pair (~2.6M rows/node/month). At that point either downsample on insert or
switch to Timescale hypertables.

### 4. Prisma schema as design doc, SQLAlchemy at runtime

See [ARCHITECTURE.md](ARCHITECTURE.md#why-prisma-ddl--sqlalchemy-runtime).
This is the most opinionated choice in the repo. The reviewer should know
the two files exist and must be kept in sync until a generator is added.

### 5. Pydantic v2 DTOs as the typed contract

Every WS event and REST response is a `pydantic.BaseModel`. The frontend
mirrors these in `apps/web/types/api.ts` by hand for now. We considered:

- OpenAPI codegen (rejected for now: brittle in monorepos, generates noisy types)
- `orval` / `openapi-typescript` (good, but adds a build step)

The hand-mirrored types are 60 lines. The codegen overhead doesn't pay off
until the surface area triples.

## Capacity & scaling

| Dimension | MVP target | Bottleneck at 10× | Path |
|---|---|---|---|
| Concurrent WS viewers | 100 | broadcaster CPU | shard by region, sticky LB |
| Sim tick rate | 1 Hz | none | trivial; we have headroom for 10 Hz |
| Nodes simulated | 50 | broadcaster payload | gzip frame, delta-encode |
| Ticks retained | 24h | Postgres write IO | downsample to 1-min after 1h |
| Workload queue depth | 10k | Redis memory | already cheap |

## Failure modes and recovery

- **Sim task crashes:** lifespan supervisor restarts it; last persisted tick
  in `energy_ticks` is the recovery anchor. State cache is reconstructed by
  replaying the last ~60s of ticks.
- **Postgres down:** writes go to a Redis spool (`arena:tick_spool`),
  drained on reconnect. Reads degrade to cache-only; analytics endpoints
  return 503 with `retry-after`.
- **Redis down:** workload submissions degrade to direct-to-Postgres
  inserts; WS still works.
- **WS disconnects:** client auto-reconnects with exponential backoff, then
  pulls `/api/energy/snapshot` to rebase.

## Observability

- All services emit structured JSON logs (`arena.core.logging`).
- The sim engine exposes `/api/health` (liveness) and `/api/health/sim`
  (last-tick-age, queue-depth, broadcaster-subscribers).
- In production, add OpenTelemetry traces around `tick()` and a Prometheus
  scrape for tick latency histograms.

## Future work

1. **Real ISO ingest** — CAISO OASIS feeds for actual curtailment numbers,
   replayable scenarios.
2. **Federated grids** — multiple sim shards exchanging surplus over a
   simulated DC↔DC market.
3. **Optimization assistant** — RAG over tick history, answers in plain
   English ("why did we route AI inference to TX-WIND-04 last hour?").
4. **L2 settlement** — every mined token / completed job emits an event
   logged to a simulated chain explorer.
