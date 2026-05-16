// Mirrors arena/schemas/*.py — keep in sync by hand for the MVP.

export type WorkloadKind = "AI_INFERENCE" | "MINING" | "DISTRIBUTED_COMPUTE";
export type WorkloadState = "QUEUED" | "RUNNING" | "DEFERRED" | "COMPLETED" | "FAILED";
export type NodeClass = "GPU_CLUSTER" | "ASIC_FARM" | "EDGE_INFERENCE" | "CPU_GRID";

export interface RegionSnapshot {
  region: string;
  name: string;
  lat: number;
  lng: number;
  generation_mw: number;
  demand_mw: number;
  surplus_mw: number;
  renewable_share: number;
}

export interface EnergySnapshot {
  timestamp: string;
  generation_mw: number;
  demand_mw: number;
  surplus_mw: number;
  renewable_share: number;
  carbon_avoided_kg: number;
  by_region: RegionSnapshot[];
}

export interface SeriesPoint { t: string; gen: number; dem: number; sur: number; }
export interface SeriesResponse { bucket_s: number; points: SeriesPoint[]; }

export interface RegionMeta {
  id: string; name: string; lat: number; lng: number;
  installed_solar_kw: number; installed_wind_kw: number; installed_hydro_kw: number;
}

export interface WorkloadDTO {
  id: string;
  kind: WorkloadKind;
  priority: number;
  demand_kw: number;
  state: WorkloadState;
  assigned_node: string | null;
  created_at: string;
  started_at: string | null;
  rationale: string | null;
}

export interface WorkloadList { items: WorkloadDTO[]; total: number; }

export interface ComputeNodeDTO {
  id: string;
  region: string;
  class_name: NodeClass;
  power_draw_kw: number;
  tflops: number;
  hashrate_ths: number;
  online: boolean;
  utilization: number;
}

export interface AllocatorExplain {
  workload_id: string;
  decision: "allocated" | "deferred" | "rejected";
  chosen_node: string | null;
  score: number;
  rationale: string;
  considered: Array<Record<string, unknown>>;
}

export interface BlockDTO {
  height: number;
  hash: string;
  miner: string;
  reward_tokens: number;
  energy_kwh: number;
  ts: string;
}

export interface BlockchainStats {
  hashrate_ths: number;
  difficulty: number;
  blocks_24h: number;
  tokens_24h: number;
  energy_kwh_24h: number;
}

export interface Sustainability {
  window: string;
  renewable_utilization_pct: number;
  energy_waste_reduction_pct: number;
  carbon_avoided_kg: number;
  grid_efficiency_delta_pct: number;
}

export interface Conversion {
  window: string;
  tflops_per_kwh: number;
  tokens_per_kwh: number;
  jobs_per_mwh: number;
}

export interface Recommendation {
  id: string;
  title: string;
  rationale: string;
  projected_impact_kg: number;
  confidence: number;
}

export interface ForecastPoint {
  region: string;
  t_offset_min: number;
  expected_surplus_mw: number;
  confidence: number;
}
export interface Forecast { horizon_min: number; points: ForecastPoint[]; }

// ─── WebSocket event envelope ───────────────────────────────────────

export interface TickPayload {
  timestamp: string;
  tick: number;
  generation_mw: number;
  demand_mw: number;
  surplus_mw: number;
  renewable_share: number;
  renewable_utilization_pct: number;
  carbon_inc_kg: number;
  carbon_total_kg: number;
  hashrate_ths: number;
  difficulty: number;
  by_region: Array<RegionSnapshot & {
    installed_solar_kw: number;
    installed_wind_kw: number;
    installed_hydro_kw: number;
  }>;
  nodes: ComputeNodeDTO[];
  workloads: WorkloadDTO[];
  block: BlockDTO | null;
  decisions: Array<{ workload_id: string; chosen_node: string; region: string; score: number; rationale: string; }>;
}

export type SimEvent =
  | { type: "hello"; v: number }
  | { type: "tick"; payload: TickPayload }
  | { type: "ping"; ts: string };
