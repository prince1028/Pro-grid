"use client";

import { Cpu, HardDrive, Pickaxe, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useTick } from "@/hooks/useTick";
import type { ComputeNodeDTO, NodeClass } from "@/types/api";
import { fmtKW, fmtNum } from "@/lib/utils";

const CLASS_META: Record<NodeClass, { label: string; icon: typeof Cpu; tone: string }> = {
  GPU_CLUSTER: { label: "GPU Cluster", icon: Sparkles, tone: "text-emerald-400" },
  ASIC_FARM: { label: "ASIC Farm", icon: Pickaxe, tone: "text-amber-400" },
  EDGE_INFERENCE: { label: "Edge", icon: Cpu, tone: "text-sky-400" },
  CPU_GRID: { label: "CPU Grid", icon: HardDrive, tone: "text-indigo-400" },
};

export default function NodesPage() {
  const { tick } = useTick(60);
  const nodes: ComputeNodeDTO[] = (tick?.nodes ?? []) as ComputeNodeDTO[];

  const grouped: Record<string, ComputeNodeDTO[]> = {};
  for (const n of nodes) (grouped[n.region] ??= []).push(n);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Nodes</h1>
        <p className="text-sm text-muted-foreground">
          Simulated distributed compute fleet. Utilization tracks live allocator decisions.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Object.entries(grouped).map(([region, list]) => (
          <Card key={region}>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>{region}</CardTitle>
              <Badge variant="outline">{list.length} nodes</Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              {list.map((n) => {
                const meta = CLASS_META[n.class_name];
                const Icon = meta.icon;
                const pct = Math.round(n.utilization * 100);
                return (
                  <div key={n.id} className="rounded-lg border border-border bg-secondary/40 p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className={`flex h-7 w-7 items-center justify-center rounded-md bg-secondary ${meta.tone}`}>
                          <Icon className="h-3.5 w-3.5" />
                        </div>
                        <div className="min-w-0">
                          <div className="font-mono text-xs truncate">{n.id}</div>
                          <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
                            {meta.label}
                          </div>
                        </div>
                      </div>
                      <Badge variant={n.online ? "success" : "destructive"}>{n.online ? "ONLINE" : "OFFLINE"}</Badge>
                    </div>
                    <div className="mt-3">
                      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                        <span>Utilization</span>
                        <span className="tabular text-foreground">{pct}%</span>
                      </div>
                      <Progress value={pct} className="mt-1" tone={pct > 90 ? "warning" : "primary"} />
                    </div>
                    <div className="mt-3 grid grid-cols-3 gap-2 text-[11px]">
                      <Stat label="Draw" value={fmtKW(n.power_draw_kw)} />
                      <Stat label="TFLOPs" value={fmtNum(n.tflops, 0)} />
                      <Stat label="Hashrate" value={`${fmtNum(n.hashrate_ths, 0)} TH/s`} />
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className="mt-0.5 tabular">{value}</div>
    </div>
  );
}
