"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Activity, ChevronRight, Cpu, Pickaxe, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useTick } from "@/hooks/useTick";
import { api } from "@/lib/api";
import { fmtKW, timeAgo } from "@/lib/utils";
import type { WorkloadDTO, WorkloadKind } from "@/types/api";

const KIND_META: Record<
  WorkloadKind,
  { label: string; icon: typeof Cpu; tone: string }
> = {
  AI_INFERENCE: { label: "AI Inference", icon: Sparkles, tone: "text-emerald-400" },
  MINING: { label: "Mining", tone: "text-amber-400", icon: Pickaxe },
  DISTRIBUTED_COMPUTE: { label: "Distributed", tone: "text-sky-400", icon: Cpu },
};

const STATE_TONE: Record<string, "default" | "outline" | "warning" | "success" | "destructive"> = {
  QUEUED: "outline",
  DEFERRED: "warning",
  RUNNING: "success",
  COMPLETED: "default",
  FAILED: "destructive",
};

export default function ComputePage() {
  const { tick } = useTick(60);
  const workloads: WorkloadDTO[] = (tick?.workloads ?? []) as WorkloadDTO[];
  const [filter, setFilter] = useState<"ALL" | "QUEUED" | "RUNNING" | "COMPLETED">("ALL");

  const filtered = useMemo(
    () => (filter === "ALL" ? workloads : workloads.filter((w) => w.state === filter)),
    [workloads, filter],
  );

  const groupCounts = useMemo(() => {
    const c: Record<string, number> = { QUEUED: 0, RUNNING: 0, DEFERRED: 0, COMPLETED: 0 };
    for (const w of workloads) c[w.state] = (c[w.state] ?? 0) + 1;
    return c;
  }, [workloads]);

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Compute</h1>
          <p className="text-sm text-muted-foreground">
            Workload allocator state and the priority queue. New jobs are matched against regional surplus each tick.
          </p>
        </div>
        <Button onClick={() => seedDemo()} variant="outline">
          <Activity className="mr-2 h-4 w-4" />
          Inject demo job
        </Button>
      </header>

      {/* Queue summary */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {(["RUNNING", "QUEUED", "DEFERRED", "COMPLETED"] as const).map((s) => (
          <Card key={s}>
            <CardContent className="p-5">
              <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{s}</div>
              <div className="mt-2 text-3xl font-semibold tabular">{groupCounts[s] ?? 0}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs value={filter} onValueChange={(v) => setFilter(v as typeof filter)}>
        <TabsList>
          <TabsTrigger value="ALL">All</TabsTrigger>
          <TabsTrigger value="RUNNING">Running</TabsTrigger>
          <TabsTrigger value="QUEUED">Queued</TabsTrigger>
          <TabsTrigger value="COMPLETED">Completed</TabsTrigger>
        </TabsList>

        <TabsContent value={filter}>
          <Card>
            <CardHeader>
              <CardTitle>Workloads ({filtered.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[440px] pr-3">
                <div className="space-y-2">
                  {filtered.length === 0 && (
                    <div className="rounded-md border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
                      No workloads in this view.
                    </div>
                  )}
                  {filtered.map((w) => (
                    <WorkloadRow key={w.id} w={w} />
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function WorkloadRow({ w }: { w: WorkloadDTO }) {
  const meta = KIND_META[w.kind];
  const Icon = meta.icon;
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-4 rounded-lg border border-border bg-secondary/40 p-3"
    >
      <div className={`flex h-9 w-9 items-center justify-center rounded-md bg-secondary ${meta.tone}`}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <div className="font-mono text-xs">{w.id}</div>
          <Badge variant={STATE_TONE[w.state] ?? "outline"}>{w.state}</Badge>
        </div>
        <div className="mt-1 truncate text-xs text-muted-foreground">
          {meta.label} · priority {(w.priority * 100).toFixed(0)} · {fmtKW(w.demand_kw)}
        </div>
        {w.rationale && (
          <div className="mt-1 truncate text-[11px] text-muted-foreground/80">{w.rationale}</div>
        )}
      </div>
      <div className="hidden flex-col items-end md:flex">
        <div className="w-32">
          <Progress
            value={Math.min(100, Math.round(w.priority * 100))}
            tone={w.state === "DEFERRED" ? "warning" : "primary"}
          />
        </div>
        <div className="mt-1 text-[10px] text-muted-foreground">
          created {timeAgo(w.created_at)}
        </div>
      </div>
      <Separator orientation="vertical" className="h-8" />
      <div className="text-right text-xs">
        <div className="font-medium">{w.assigned_node ?? "—"}</div>
        <div className="text-[10px] text-muted-foreground">node</div>
      </div>
      <ChevronRight className="h-4 w-4 text-muted-foreground" />
    </motion.div>
  );
}

function seedDemo() {
  const kinds: WorkloadKind[] = ["AI_INFERENCE", "MINING", "DISTRIBUTED_COMPUTE"];
  const kind = kinds[Math.floor(Math.random() * kinds.length)];
  const priority = Math.random();
  const demand = kind === "MINING" ? 400 : kind === "AI_INFERENCE" ? 180 : 120;
  api.createWorkload({ kind, priority, demand_kw: demand }).catch(() => {});
}
