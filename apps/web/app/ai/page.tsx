"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Brain, MessageSquare, Sparkles, TrendingUp } from "lucide-react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { fmtNum, fmtPctNum } from "@/lib/utils";
import type { Forecast, ForecastPoint, Recommendation } from "@/types/api";

export default function AIPage() {
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [explainTarget, setExplainTarget] = useState<string>("");
  const [explanation, setExplanation] = useState<string>("");

  useEffect(() => {
    const load = async () => {
      try {
        const [r, f] = await Promise.all([api.recommendations(), api.forecast("60m")]);
        setRecs(r);
        setForecast(f);
      } catch {}
    };
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  const pivot = pivotForecast(forecast?.points ?? []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">AI optimization</h1>
        <p className="text-sm text-muted-foreground">
          Recommendations, surplus forecasts, and plain-English explanations of allocator decisions.
        </p>
      </header>

      {/* Recommendations */}
      <div>
        <h2 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
          <Sparkles className="h-4 w-4" /> Top recommendations
        </h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {recs.map((r, i) => (
            <motion.div
              key={r.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Card>
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="font-medium">{r.title}</div>
                    <Badge>{fmtPctNum(r.confidence * 100, 0)}</Badge>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{r.rationale}</p>
                  <div className="mt-3 flex items-center gap-1 text-xs text-emerald-400">
                    <TrendingUp className="h-3 w-3" />
                    {fmtNum(r.projected_impact_kg, 1)} kg CO₂ avoided
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Forecast */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-4 w-4 text-primary" /> Surplus forecast (60 min)
          </CardTitle>
          <Badge variant="outline">EWMA + diurnal</Badge>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={pivot.data} margin={{ top: 12, right: 8, left: -16, bottom: 0 }}>
              <XAxis dataKey="t" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 10 }} />
              <YAxis
                stroke="hsl(var(--muted-foreground))"
                tick={{ fontSize: 10 }}
                tickFormatter={(v: number) => `${Math.round(v)} MW`}
                width={64}
              />
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(v: number, n: string) => [`${v.toFixed(0)} MW`, n]}
              />
              {pivot.regions.map((r, i) => (
                <Line
                  key={r}
                  type="monotone"
                  dataKey={r}
                  stroke={REGION_COLORS[i % REGION_COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Explain */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-primary" /> Explain an allocation
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="wl_xxxxx"
              value={explainTarget}
              onChange={(e) => setExplainTarget(e.target.value)}
              className="h-9 flex-1 rounded-md border border-input bg-background px-3 text-sm font-mono outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <Button
              onClick={async () => {
                if (!explainTarget) return;
                try {
                  const r = await api.explain("allocation", explainTarget);
                  setExplanation(r.explanation);
                } catch (e) {
                  setExplanation(String(e));
                }
              }}
            >
              Explain
            </Button>
          </div>
          {explanation && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-md border border-border bg-secondary/40 p-3 text-sm"
            >
              {explanation}
            </motion.div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

const REGION_COLORS = [
  "hsl(152 70% 50%)",
  "hsl(38 100% 60%)",
  "hsl(195 90% 60%)",
  "hsl(280 80% 65%)",
];

function pivotForecast(points: ForecastPoint[]) {
  const byOffset = new Map<number, Record<string, number>>();
  const regions = new Set<string>();
  for (const p of points) {
    regions.add(p.region);
    if (!byOffset.has(p.t_offset_min)) byOffset.set(p.t_offset_min, {});
    byOffset.get(p.t_offset_min)![p.region] = p.expected_surplus_mw;
  }
  const data = Array.from(byOffset.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([offset, rec]) => ({ t: `+${offset}m`, ...rec }));
  return { data, regions: Array.from(regions) };
}
