"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Cloud, CloudLightning, Cpu, Leaf, Sun, Wind, Zap } from "lucide-react";
import { EnergyAreaChart } from "@/components/charts/EnergyAreaChart";
import { RegionBarChart } from "@/components/charts/RegionBarChart";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { RegionMap } from "@/components/dashboard/RegionMap";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTick } from "@/hooks/useTick";
import { fmtCarbon, fmtMW, fmtNum, fmtPctNum } from "@/lib/utils";
import { api } from "@/lib/api";
import type { SeriesPoint } from "@/types/api";

export default function EnergyDashboard() {
  const { tick, history, connected } = useTick(180);
  const [series, setSeries] = useState<SeriesPoint[]>([]);

  // Seed the chart with persisted series until enough ticks accumulate live.
  useEffect(() => {
    api
      .energySeries("1h", 60)
      .then((r) => setSeries(r.points))
      .catch(() => {});
  }, []);

  // Combine persisted series with live history for a smoother feel.
  const liveSeries: SeriesPoint[] = [
    ...series,
    ...history.slice(-60).map((h) => ({
      t: h.timestamp,
      gen: h.generation_mw,
      dem: h.demand_mw,
      sur: h.surplus_mw,
    })),
  ];

  const regions = tick?.by_region ?? [];
  const totalSolar = regions.reduce((a, r) => a + (r.installed_solar_kw ?? 0), 0) / 1000;
  const totalWind = regions.reduce((a, r) => a + (r.installed_wind_kw ?? 0), 0) / 1000;
  const totalHydro = regions.reduce((a, r) => a + (r.installed_hydro_kw ?? 0), 0) / 1000;

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Energy</h1>
          <p className="text-sm text-muted-foreground">
            Live renewable generation, demand, and surplus across simulated regions.
          </p>
        </div>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: connected ? 1 : 0.5 }}
          className="text-xs text-muted-foreground"
        >
          Tick #{tick?.tick ?? 0} · {tick ? new Date(tick.timestamp).toLocaleTimeString() : "—"}
        </motion.div>
      </header>

      {/* KPIs */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Total generation"
          value={tick ? fmtMW(tick.generation_mw) : "—"}
          tone="primary"
          icon={Zap}
          sub={`${fmtPctNum(tick ? tick.renewable_share * 100 : 0, 0)} renewable`}
        />
        <KpiCard
          label="Surplus"
          value={tick ? fmtMW(tick.surplus_mw) : "—"}
          tone={tick && tick.surplus_mw < 0 ? "danger" : "primary"}
          icon={CloudLightning}
          sub={tick && tick.surplus_mw < 0 ? "Grid in deficit" : "Available for compute"}
        />
        <KpiCard
          label="Renewable utilization"
          value={tick ? fmtPctNum(tick.renewable_utilization_pct, 1) : "—"}
          tone="primary"
          icon={Leaf}
          sub="Generation actually served"
        />
        <KpiCard
          label="Carbon avoided"
          value={tick ? fmtCarbon(tick.carbon_total_kg) : "—"}
          tone="primary"
          icon={Cpu}
          sub="Cumulative since boot"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Generation · Demand · Surplus</CardTitle>
          </CardHeader>
          <CardContent>
            <EnergyAreaChart data={liveSeries} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Surplus by region</CardTitle>
          </CardHeader>
          <CardContent>
            <RegionBarChart
              data={regions.map((r) => ({ region: r.region, surplus_mw: r.surplus_mw }))}
            />
          </CardContent>
        </Card>
      </div>

      {/* Region map + installed capacity */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <RegionMap
          regions={regions.map((r) => ({
            region: r.region,
            name: r.name,
            lat: r.lat,
            lng: r.lng,
            generation_mw: r.generation_mw,
            surplus_mw: r.surplus_mw,
            renewable_share: r.renewable_share,
          }))}
        />
        <Card>
          <CardHeader>
            <CardTitle>Installed capacity</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <CapRow icon={Sun} label="Solar" tone="text-amber-400" mw={totalSolar} />
            <CapRow icon={Wind} label="Wind" tone="text-sky-400" mw={totalWind} />
            <CapRow icon={Cloud} label="Hydro" tone="text-indigo-400" mw={totalHydro} />
            <div className="mt-4 rounded-lg border border-border bg-secondary/30 p-3 text-xs text-muted-foreground">
              Fleet nameplate:{" "}
              <span className="text-foreground tabular">
                {fmtNum(totalSolar + totalWind + totalHydro, 0)} MW
              </span>{" "}
              across {regions.length} regions.
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function CapRow({
  icon: Icon,
  label,
  tone,
  mw,
}: {
  icon: typeof Sun;
  label: string;
  tone: string;
  mw: number;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Icon className={`h-4 w-4 ${tone}`} />
        <span className="text-sm">{label}</span>
      </div>
      <span className="text-sm tabular text-muted-foreground">{fmtMW(mw)}</span>
    </div>
  );
}
