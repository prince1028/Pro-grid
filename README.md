# ARENA-GRID

**Renewable-powered compute. Surplus energy, allocated.**

ARENA-GRID is a deep-tech simulation platform that demonstrates how surplus
renewable energy (solar / wind / hydro) can dynamically dispatch compute
workloads — AI inference, distributed jobs, and tokenized mining — to
**absorb generation that would otherwise be curtailed**.

It is built as a vertical-slice MVP: an end-to-end realtime simulation with a
production-shaped architecture (service / repository layers, WebSocket fanout,
Redis-backed queues, Dockerized services) and a polished operator dashboard.

---

## Why this exists

> Wind and solar farms routinely **curtail** generation when the grid can't
> absorb it. In California (CAISO) and Texas (ERCOT) combined, **multiple
> terawatt-hours** of clean energy are spilled every year. That energy is
> free, zero-carbon, and stranded.

ARENA-GRID asks: **what if every megawatt of curtailment got auctioned to a
compute workload in milliseconds?** Renewable surplus becomes the cheapest
input to AI training, scientific computing, and tokenized value generation —
and the grid stops bleeding free energy.

This repo simulates that loop end-to-end.

---

## What's inside

| Layer | Stack |
|---|---|
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind, shadcn/ui, Framer Motion, Recharts |
| Backend | FastAPI (Python 3.11), async SQLAlchemy, Pydantic v2, WebSockets |
| Data | PostgreSQL 16 (schema authored in Prisma), Redis 7 (queues + pub/sub) |
| Infra | Local dev (uvicorn + `next dev`), modular service layout |
| Sim   | Async tick loop, priority allocator, mining/AI workload models, forecaster |

```
arena-grid/
├── apps/
│   ├── web/        Next.js 15 dashboard
│   └── api/        FastAPI simulation engine + REST + WS
├── docs/           Architecture, system design, API reference
├── scripts/        Seed + dev helpers
├── docker-compose.yml
└── .env.example
```

---

## Features

### Implemented (vertical slice)
- **Realtime energy dashboard** — solar/wind generation, demand, surplus/deficit, region map, live WebSocket feed
- **Distributed compute allocator** — priority queue across AI inference, mining, and distributed-compute workloads, demand-response aware
- **Node fleet** — simulated heterogeneous nodes (GPU clusters, ASIC farms, edge nodes) with live utilization
- **Carbon + utilization scoring** — gCO₂/kWh avoided, renewable-utilization %, mining profitability
- **Smart-grid optimization loop** — DER balancing tick, predictive surplus windows
- **Research analytics** — sustainability KPIs, energy-waste-reduction %, grid-efficiency delta
- **AI recommendations** — optimization suggestions + plain-English explanations of allocator decisions

### Polished skeletons (extensible)
- Blockchain explorer simulation
- Renewable energy marketplace
- Time-series playback / replay
- Optimization-assistant chatbot

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md).

---

## Quick start (local)

You need: **Python 3.11+**, **Node 20+**, **PostgreSQL 16**, **Redis 7**.
(SQLite + in-memory pubsub fallbacks are also supported — see below.)

```powershell
# 1) copy env
cp .env.example .env

# 2) backend
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn arena.main:app --reload --port 8000
```

In a second terminal:

```powershell
# 3) frontend
cd apps/web
npm install
npm run dev
```

Then open:

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API       | http://localhost:8000 |
| API docs  | http://localhost:8000/docs |
| WebSocket | ws://localhost:8000/ws/sim |

On first boot the API auto-seeds: renewable nodes across 4 regions, simulated compute nodes, and a baseline workload backlog.

### Zero-dependency mode

If you don't want to install Postgres/Redis, set in `.env`:

```
DATABASE_URL=sqlite+aiosqlite:///./arena.db
REDIS_URL=memory://
```

The API falls back to SQLite and an in-process pub/sub. Everything still works; you just lose durability across restarts.

---

## Architecture at a glance

```
┌──────────────┐    REST / WS     ┌──────────────────┐    pub/sub     ┌─────────┐
│  Next.js 15  │ ───────────────▶ │  FastAPI gateway │ ─────────────▶ │  Redis  │
│  dashboard   │ ◀─────────────── │  + WS hub        │ ◀───────────── │ streams │
└──────────────┘   realtime tick  └────────┬─────────┘                 └─────────┘
                                           │
                                  ┌────────┴─────────┐
                                  │  Sim engine      │      async tick loop, 1Hz
                                  │  • energy_sim    │
                                  │  • allocator     │
                                  │  • mining_sim    │
                                  │  • forecaster    │
                                  └────────┬─────────┘
                                           │
                                  ┌────────┴─────────┐
                                  │  Repositories    │ ─── PostgreSQL (Prisma schema)
                                  └──────────────────┘
```

The simulation engine ticks once per second:

1. **`energy_sim`** advances solar/wind generation per region using diurnal + stochastic models
2. **`allocator`** drains the workload priority queue against available surplus (kWh), respecting node capabilities
3. **`mining_sim`** computes hashrate × difficulty → simulated token yield
4. **`forecaster`** projects the next 60 minutes of surplus using a rolling EWMA
5. The tick result is written to Postgres (time-series) and broadcast over the WS hub

See [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) for the full design, tradeoffs, and scalability discussion.

---

## API

OpenAPI docs auto-generated at `/docs` and `/redoc`.

See [docs/API.md](docs/API.md) for the curated endpoint reference and example payloads.

---

## Testing

```bash
cd apps/api
pytest
```

Backend ships with unit tests for the allocator priority logic and the energy simulator.

---

## Deployment notes

- Front API behind a TLS-terminating reverse proxy (Caddy / Cloudflare)
- Run `web` as a Next.js standalone build, served by Node 20
- Run `api` under uvicorn workers (`--workers $(nproc)`) behind a healthchecked LB
- Use a managed Redis with persistence (AOF) for queue durability
- Use a managed Postgres with `pg_stat_statements` enabled

---

## Roadmap

- [ ] Replay mode + scenario library (heatwave / wind drought / negative-price events)
- [ ] Live integration with real ISO feeds (CAISO OASIS, ERCOT MIS)
- [ ] Optimization assistant chatbot grounded on tick history
- [ ] L2 settlement for marketplace bids
- [ ] Multi-region federation across simulated grids

---

## License

MIT — see [LICENSE](LICENSE).
