"use client";

import { motion } from "framer-motion";
import { Radio } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useTick } from "@/hooks/useTick";
import { fmtMW, fmtPctNum } from "@/lib/utils";

export function Topbar() {
  const { tick, connected } = useTick(60);
  return (
    <div className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b border-border bg-background/70 px-6 backdrop-blur-xl">
      <div className="flex items-center gap-4">
        <h1 className="text-sm font-medium text-muted-foreground">Live grid simulation</h1>
        <div className="flex items-center gap-2">
          <motion.span
            className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-400" : "bg-amber-500"}`}
            animate={{ scale: connected ? [1, 1.3, 1] : 1 }}
            transition={{ duration: 1.6, repeat: Infinity }}
          />
          <span className="text-xs text-muted-foreground">
            {connected ? "Realtime stream" : "Reconnecting…"}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-6 tabular">
        <Metric label="Generation" value={tick ? fmtMW(tick.generation_mw) : "—"} tone="text-foreground" />
        <Metric
          label="Surplus"
          value={tick ? fmtMW(tick.surplus_mw) : "—"}
          tone={tick && tick.surplus_mw < 0 ? "text-red-400" : "text-emerald-400"}
        />
        <Metric
          label="Renewable"
          value={tick ? fmtPctNum(tick.renewable_share * 100, 0) : "—"}
          tone="text-foreground"
        />
        <Badge variant="outline" className="hidden lg:inline-flex">
          <Radio className="mr-1 h-3 w-3" />
          tick #{tick?.tick ?? "—"}
        </Badge>
      </div>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="flex flex-col items-end">
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className={`text-sm font-medium ${tone}`}>{value}</div>
    </div>
  );
}
