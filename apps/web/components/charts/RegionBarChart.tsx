"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface RegionBarPoint {
  region: string;
  surplus_mw: number;
}

export function RegionBarChart({ data }: { data: RegionBarPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 10, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 4" vertical={false} />
        <XAxis dataKey="region" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 10 }} />
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
          formatter={(v: number) => [`${v.toFixed(0)} MW`, "Surplus"]}
        />
        <Bar dataKey="surplus_mw" radius={[6, 6, 0, 0]}>
          {data.map((d) => (
            <Cell
              key={d.region}
              fill={d.surplus_mw >= 0 ? "hsl(152 70% 50%)" : "hsl(0 75% 60%)"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
