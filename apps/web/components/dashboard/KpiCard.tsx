"use client";

import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: string;
  delta?: string;
  tone?: "primary" | "warning" | "danger" | "default";
  icon?: LucideIcon;
  sub?: string;
}

const toneClasses: Record<NonNullable<KpiCardProps["tone"]>, string> = {
  primary: "text-emerald-400",
  warning: "text-amber-400",
  danger: "text-red-400",
  default: "text-foreground",
};

export function KpiCard({ label, value, delta, tone = "default", icon: Icon, sub }: KpiCardProps) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
              {label}
            </div>
            <motion.div
              key={value}
              initial={{ opacity: 0.4, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className={cn("mt-2 text-3xl font-semibold tabular", toneClasses[tone])}
            >
              {value}
            </motion.div>
            {sub && <div className="mt-1 text-xs text-muted-foreground">{sub}</div>}
          </div>
          {Icon && (
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-secondary text-muted-foreground">
              <Icon className="h-4 w-4" />
            </div>
          )}
        </div>
        {delta && (
          <div className="mt-3 text-xs text-muted-foreground">
            <span className={tone === "danger" ? "text-red-400" : "text-emerald-400"}>{delta}</span>{" "}
            vs prior tick
          </div>
        )}
      </CardContent>
    </Card>
  );
}
