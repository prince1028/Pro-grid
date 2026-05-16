"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface EnergyPoint {
  t: string;
  gen: number;
  dem: number;
  sur: number;
}

export function EnergyAreaChart({ data }: { data: EnergyPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ top: 10, right: 8, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="gen" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(152 70% 50%)" stopOpacity={0.5} />
            <stop offset="100%" stopColor="hsl(152 70% 50%)" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="dem" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(195 90% 60%)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="hsl(195 90% 60%)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 4" vertical={false} />
        <XAxis
          dataKey="t"
          tickFormatter={(s: string) =>
            new Date(s).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
          }
          stroke="hsl(var(--muted-foreground))"
          tick={{ fontSize: 10 }}
          minTickGap={36}
        />
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
          labelFormatter={(v: string) => new Date(v).toLocaleString()}
          formatter={(value: number, name: string) => [`${value.toFixed(0)} MW`, name]}
        />
        <Area type="monotone" dataKey="gen" name="Generation" stroke="hsl(152 70% 50%)" fill="url(#gen)" strokeWidth={2} />
        <Area type="monotone" dataKey="dem" name="Demand" stroke="hsl(195 90% 60%)" fill="url(#dem)" strokeWidth={2} />
        <Area type="monotone" dataKey="sur" name="Surplus" stroke="hsl(38 100% 60%)" fill="transparent" strokeDasharray="4 3" strokeWidth={1.5} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
