"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Brain,
  Cpu,
  Gauge,
  HardDrive,
  Layers,
  LineChart,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/", label: "Energy", icon: Zap },
  { href: "/compute", label: "Compute", icon: Cpu },
  { href: "/nodes", label: "Nodes", icon: HardDrive },
  { href: "/blockchain", label: "Blockchain", icon: Layers },
  { href: "/analytics", label: "Analytics", icon: LineChart },
  { href: "/ai", label: "AI", icon: Brain },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden md:flex md:w-60 shrink-0 flex-col border-r border-border bg-card/40 backdrop-blur-xl">
      <div className="flex h-16 items-center gap-2 px-5 border-b border-border">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/15 text-primary">
          <Gauge className="h-4 w-4" />
        </div>
        <div>
          <div className="text-sm font-semibold tracking-wide">ARENA-GRID</div>
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
            Operator console
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {nav.map((n) => {
          const active = pathname === n.href || (n.href !== "/" && pathname.startsWith(n.href));
          const Icon = n.icon;
          return (
            <Link
              key={n.href}
              href={n.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{n.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-4 text-[11px] text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <Activity className="h-3 w-3 text-primary" />
          <span>v0.1.0 · MVP</span>
        </div>
        <div className="mt-1">Renewable surplus, allocated.</div>
      </div>
    </aside>
  );
}
