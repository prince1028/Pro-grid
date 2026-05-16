"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtMW, fmtPctNum } from "@/lib/utils";

interface Region {
  region: string;
  name: string;
  lat: number;
  lng: number;
  generation_mw: number;
  surplus_mw: number;
  renewable_share: number;
}

// Project (lng, lat) into a 0..1 canvas with a tasteful Equirectangular squish.
function project(lat: number, lng: number) {
  const x = (lng + 180) / 360;
  const y = (90 - lat) / 180;
  // Crunch vertically and pad horizontally so the dots sit in a wide strip.
  return { x: 0.05 + 0.9 * x, y: 0.2 + 0.6 * y };
}

export function RegionMap({ regions }: { regions: Region[] }) {
  return (
    <Card className="lg:col-span-2">
      <CardHeader>
        <CardTitle>Region map</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative aspect-[3/1.4] w-full overflow-hidden rounded-lg border border-border bg-gradient-to-b from-secondary/30 to-background">
          {/* Decorative grid */}
          <svg className="absolute inset-0 h-full w-full opacity-30">
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M40 0H0V40" fill="none" stroke="hsl(var(--border))" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
          </svg>

          {regions.map((r) => {
            const { x, y } = project(r.lat, r.lng);
            const tone =
              r.surplus_mw > 100
                ? "bg-emerald-400"
                : r.surplus_mw > 0
                  ? "bg-amber-400"
                  : "bg-red-400";
            return (
              <div
                key={r.region}
                className="absolute -translate-x-1/2 -translate-y-1/2"
                style={{ left: `${x * 100}%`, top: `${y * 100}%` }}
              >
                <motion.div
                  className={`relative h-3.5 w-3.5 rounded-full ${tone}`}
                  animate={{ scale: [1, 1.25, 1] }}
                  transition={{ duration: 2.6, repeat: Infinity }}
                >
                  <span
                    className={`absolute inset-0 -m-2 rounded-full ${tone} opacity-30 blur-md`}
                  />
                </motion.div>
                <div className="mt-2 -translate-x-1/2 transform whitespace-nowrap text-[10px]">
                  <div className="font-medium">{r.name}</div>
                  <div className="tabular text-muted-foreground">
                    {fmtMW(r.surplus_mw)} · {fmtPctNum(r.renewable_share * 100, 0)}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
