# API Reference

Full interactive docs at `http://localhost:8000/docs` (OpenAPI 3) and
`http://localhost:8000/redoc`. This file is a curated summary.

Base URL: `http://localhost:8000`

## Conventions

- All responses are JSON.
- Timestamps are ISO-8601 UTC.
- Errors follow `{ "error": { "code": "...", "message": "...", "details": {} } }`.

---

## `GET /api/health`

Liveness probe.

```json
{ "status": "ok", "uptime_s": 1287.4, "version": "0.1.0" }
```

## `GET /api/health/sim`

Sim engine status (readiness).

```json
{
  "ticking": true,
  "last_tick_at": "2026-05-16T14:22:01Z",
  "last_tick_age_ms": 412,
  "ws_subscribers": 3,
  "queue_depth": 12
}
```

---

## Energy

### `GET /api/energy/snapshot`

Latest aggregate generation, demand, and surplus across all regions.

```json
{
  "timestamp": "2026-05-16T14:22:01Z",
  "generation_mw": 4827.3,
  "demand_mw": 3941.0,
  "surplus_mw": 886.3,
  "renewable_share": 0.78,
  "by_region": [
    {"region": "CA-NORTH",  "generation_mw": 1402.1, "surplus_mw": 312.8},
    {"region": "TX-WEST",   "generation_mw": 1893.0, "surplus_mw": 401.2},
    {"region": "EU-NORDIC", "generation_mw":  892.0, "surplus_mw":  88.4},
    {"region": "AU-SE",     "generation_mw":  640.2, "surplus_mw":  83.9}
  ]
}
```

### `GET /api/energy/series?window=1h&bucket=1m`

Time-series for charting. `window` ∈ {`5m`, `1h`, `24h`}, `bucket` is the
downsampling interval.

```json
{
  "bucket_s": 60,
  "points": [
    {"t": "2026-05-16T13:22:00Z", "gen": 4710.0, "dem": 3900.0, "sur": 810.0},
    ...
  ]
}
```

### `GET /api/energy/regions`

Static metadata: region id, name, lat/lng, installed capacity per source.

---

## Compute

### `GET /api/compute/workloads`

Lists active workloads with priority, type, and allocation state.

```json
{
  "items": [
    {
      "id": "wl_abc123",
      "kind": "ai_inference",
      "priority": 0.91,
      "demand_kw": 220,
      "state": "running",
      "assigned_node": "node_gpu_07",
      "started_at": "2026-05-16T14:18:00Z"
    }
  ],
  "total": 27
}
```

### `POST /api/compute/workloads`

Enqueue a workload. Validated against the allocator's capability map.

```json
// request
{ "kind": "mining", "priority": 0.4, "demand_kw": 80 }

// 201 response
{ "id": "wl_xyz789", "state": "queued" }
```

### `GET /api/compute/allocator/explain?workload_id=wl_xyz789`

Returns the allocator's decision trace for a workload — used by the
"Explain" panel on the AI page.

---

## Nodes

### `GET /api/nodes`

Fleet inventory with live utilization.

### `GET /api/nodes/{id}`

Single-node detail incl. last 5 minutes of utilization.

---

## Blockchain (simulation)

### `GET /api/blockchain/blocks?limit=20`

Most recent simulated blocks.

### `GET /api/blockchain/stats`

Hashrate, simulated difficulty, tokens emitted last 24h.

---

## Analytics

### `GET /api/analytics/sustainability`

```json
{
  "window": "24h",
  "renewable_utilization_pct": 87.2,
  "energy_waste_reduction_pct": 41.6,
  "carbon_avoided_kg": 18420.7,
  "grid_efficiency_delta_pct": 6.4
}
```

### `GET /api/analytics/conversion`

Compute-to-energy conversion: useful work (TFLOPs, tokens, jobs) per kWh.

---

## AI

### `GET /api/ai/recommendations`

Optimization suggestions ranked by projected impact.

### `GET /api/ai/forecast?horizon=60m`

Forecasted surplus for the next N minutes, per region.

### `POST /api/ai/explain`

```json
{ "subject": "allocation", "id": "wl_xyz789" }
```

Returns a plain-English rationale.

---

## WebSocket: `/ws/sim`

Frame format:

```json
{ "type": "tick", "payload": { /* SnapshotEvent — same shape as /energy/snapshot, plus deltas */ } }
```

Heartbeat every 10s:

```json
{ "type": "ping", "ts": "2026-05-16T14:22:01Z" }
```

Clients may send `{ "type": "subscribe", "channels": ["energy", "compute"] }`
to scope traffic — default is all channels.
