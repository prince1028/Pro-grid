"use client";

import { useEffect, useState } from "react";
import { CloudLightning, Gauge, Leaf, Recycle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { api } from "@/lib/api";
import { fmtCarbon, fmtNum, fmtPctNum } from "@/lib/utils";
import type { Conversion, Sustainability } from "@/types/api";

export default function AnalyticsPage() {
  const [sus, setSus] = useState<Sustainability | null>(null);
  const [conv, setConv] = useState<Conversion | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [s, c] = await Promise.all([api.sustainability("24h"), api.conversion("1h")]);
        setSus(s);
        setConv(c);
      } catch {}
    };
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Research analytics</h1>
        <p className="text-sm text-muted-foreground">
          Sustainability metrics and compute-to-energy conversion. Aggregated over the rolling window.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Renewable utilization"
          value={sus ? fmtPctNum(sus.renewable_utilization_pct, 1) : "—"}
          tone="primary"
          icon={Leaf}
        />
        <KpiCard
          label="Energy-waste reduction"
          value={sus ? fmtPctNum(sus.energy_waste_reduction_pct, 1) : "—"}
          tone="primary"
          icon={Recycle}
          sub="vs. 60% baseline"
        />
        <KpiCard
          label="Carbon avoided"
          value={sus ? fmtCarbon(sus.carbon_avoided_kg) : "—"}
          icon={CloudLightning}
          tone="primary"
        />
        <KpiCard
          label="Grid efficiency Δ"
          value={sus ? fmtPctNum(sus.grid_efficiency_delta_pct, 2) : "—"}
          icon={Gauge}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Compute-to-energy conversion</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <ConvRow label="TFLOPs / kWh" value={conv ? fmtNum(conv.tflops_per_kwh, 2) : "—"} />
          <ConvRow label="Tokens / kWh" value={conv ? fmtNum(conv.tokens_per_kwh, 4) : "—"} />
          <ConvRow label="Jobs / MWh" value={conv ? fmtNum(conv.jobs_per_mwh, 2) : "—"} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>How these numbers are computed</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            <strong className="text-foreground">Renewable utilization</strong> is generation actually
            served (demand + matched compute load) divided by total generation, fleet-wide.
          </p>
          <p>
            <strong className="text-foreground">Energy-waste reduction</strong> compares the current
            utilization against a curtailment-prone baseline of 60% — i.e., the share of generation
            that would have been spilled without dispatchable compute.
          </p>
          <p>
            <strong className="text-foreground">Carbon avoided</strong> uses a U.S.-grid-average
            displacement factor of 0.40 kg CO₂ per kWh of renewable energy that replaced fossil.
          </p>
          <p>
            <strong className="text-foreground">Conversion metrics</strong> are aggregated across
            online nodes weighted by current utilization.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function ConvRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className="mt-2 text-3xl font-semibold tabular text-emerald-400">{value}</div>
    </div>
  );
}
