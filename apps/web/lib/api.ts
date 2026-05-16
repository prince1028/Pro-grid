import { API_URL } from "./env";
import type {
  BlockchainStats,
  BlockDTO,
  ComputeNodeDTO,
  Conversion,
  EnergySnapshot,
  Forecast,
  Recommendation,
  RegionMeta,
  SeriesResponse,
  Sustainability,
  WorkloadKind,
  WorkloadList,
} from "@/types/api";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status} ${res.statusText} on ${path}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // Energy
  energySnapshot: () => http<EnergySnapshot>("/api/energy/snapshot"),
  energySeries: (window: "5m" | "1h" | "24h" = "1h", bucket = 60, region?: string) =>
    http<SeriesResponse>(
      `/api/energy/series?window=${window}&bucket=${bucket}${region ? `&region=${region}` : ""}`,
    ),
  regions: () => http<RegionMeta[]>("/api/energy/regions"),

  // Compute
  workloads: (state?: string) =>
    http<WorkloadList>(`/api/compute/workloads${state ? `?state=${state}` : ""}`),
  createWorkload: (body: { kind: WorkloadKind; priority: number; demand_kw: number }) =>
    http<{ id: string; state: string }>("/api/compute/workloads", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  explainAllocation: (workloadId: string) =>
    http<{
      workload_id: string;
      decision: string;
      chosen_node: string | null;
      score: number;
      rationale: string;
      considered: Array<Record<string, unknown>>;
    }>(`/api/compute/allocator/explain?workload_id=${encodeURIComponent(workloadId)}`),

  // Nodes
  nodes: () => http<ComputeNodeDTO[]>("/api/nodes"),

  // Blockchain
  blocks: (limit = 20) => http<BlockDTO[]>(`/api/blockchain/blocks?limit=${limit}`),
  blockchainStats: () => http<BlockchainStats>("/api/blockchain/stats"),

  // Analytics
  sustainability: (window: "1h" | "24h" = "24h") =>
    http<Sustainability>(`/api/analytics/sustainability?window=${window}`),
  conversion: (window: "1h" | "24h" = "1h") =>
    http<Conversion>(`/api/analytics/conversion?window=${window}`),

  // AI
  recommendations: () => http<Recommendation[]>("/api/ai/recommendations"),
  forecast: (horizon: "15m" | "30m" | "60m" | "2h" = "60m") =>
    http<Forecast>(`/api/ai/forecast?horizon=${horizon}`),
  explain: (subject: string, id: string) =>
    http<{ subject: string; id: string; explanation: string }>("/api/ai/explain", {
      method: "POST",
      body: JSON.stringify({ subject, id }),
    }),

  // Health
  health: () => http<{ status: string; uptime_s: number; version: string }>("/api/health"),
  simHealth: () =>
    http<{
      ticking: boolean;
      last_tick_at: string | null;
      last_tick_age_ms: number | null;
      tick_count: number;
      ws_subscribers: number;
    }>("/api/health/sim"),
};
