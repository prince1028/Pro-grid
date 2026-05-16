"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Hash, Layers, Pickaxe, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { useTick } from "@/hooks/useTick";
import { api } from "@/lib/api";
import { fmtNum, shortHash, timeAgo } from "@/lib/utils";
import type { BlockchainStats, BlockDTO } from "@/types/api";

export default function BlockchainPage() {
  const { tick } = useTick(60);
  const [blocks, setBlocks] = useState<BlockDTO[]>([]);
  const [stats, setStats] = useState<BlockchainStats | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [b, s] = await Promise.all([api.blocks(30), api.blockchainStats()]);
        setBlocks(b);
        setStats(s);
      } catch {}
    };
    load();
    const id = setInterval(load, 4000);
    return () => clearInterval(id);
  }, []);

  // If a new block was emitted on the live tick, prepend optimistically.
  useEffect(() => {
    const fresh = tick?.block;
    if (!fresh) return;
    setBlocks((b) => {
      if (b.length && b[0].hash === fresh.hash) return b;
      const top = b[0]?.height ?? 0;
      return [
        { height: top + 1, hash: fresh.hash, miner: fresh.miner, reward_tokens: fresh.reward_tokens, energy_kwh: fresh.energy_kwh, ts: fresh.ts },
        ...b,
      ].slice(0, 30);
    });
  }, [tick?.block]);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Blockchain</h1>
        <p className="text-sm text-muted-foreground">
          Simulated tokenized value layer — blocks minted by mining workloads running on renewable surplus.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Hashrate" value={`${fmtNum(stats?.hashrate_ths ?? 0, 1)} TH/s`} icon={Zap} tone="primary" />
        <KpiCard label="Difficulty" value={fmtNum(stats?.difficulty ?? 0, 0)} icon={Hash} />
        <KpiCard label="Blocks 24h" value={fmtNum(stats?.blocks_24h ?? 0, 0)} icon={Layers} tone="primary" />
        <KpiCard
          label="Tokens 24h"
          value={fmtNum(stats?.tokens_24h ?? 0, 2)}
          icon={Pickaxe}
          tone="primary"
          sub={`${fmtNum(stats?.energy_kwh_24h ?? 0, 1)} kWh used`}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Block explorer</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full table-fixed text-xs">
              <thead className="bg-secondary/60 text-[10px] uppercase tracking-widest text-muted-foreground">
                <tr>
                  <th className="w-20 px-3 py-2 text-left">Height</th>
                  <th className="px-3 py-2 text-left">Hash</th>
                  <th className="px-3 py-2 text-left">Miner</th>
                  <th className="px-3 py-2 text-right">Reward</th>
                  <th className="px-3 py-2 text-right">Energy</th>
                  <th className="w-24 px-3 py-2 text-right">Time</th>
                </tr>
              </thead>
              <tbody>
                {blocks.length === 0 && (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-muted-foreground">
                      No blocks yet. Add a mining workload on the Compute page.
                    </td>
                  </tr>
                )}
                {blocks.map((b, i) => (
                  <motion.tr
                    key={b.hash}
                    initial={i === 0 ? { backgroundColor: "rgba(16,185,129,0.15)" } : undefined}
                    animate={{ backgroundColor: "rgba(0,0,0,0)" }}
                    transition={{ duration: 1.4 }}
                    className="border-t border-border tabular"
                  >
                    <td className="px-3 py-2 font-mono">{b.height}</td>
                    <td className="px-3 py-2 font-mono truncate">{shortHash(b.hash)}</td>
                    <td className="px-3 py-2 font-mono truncate">{b.miner}</td>
                    <td className="px-3 py-2 text-right">{fmtNum(b.reward_tokens, 4)}</td>
                    <td className="px-3 py-2 text-right">{fmtNum(b.energy_kwh, 2)} kWh</td>
                    <td className="px-3 py-2 text-right text-muted-foreground">{timeAgo(b.ts)}</td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex justify-end">
            <Badge variant="outline">Simulation · L1 toy chain</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
