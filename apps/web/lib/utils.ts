import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmtMW(mw: number, digits = 0): string {
  if (Math.abs(mw) >= 1000) return `${(mw / 1000).toFixed(digits + 1)} GW`;
  return `${mw.toFixed(digits)} MW`;
}

export function fmtKW(kw: number, digits = 0): string {
  if (Math.abs(kw) >= 1000) return `${(kw / 1000).toFixed(digits + 1)} MW`;
  return `${kw.toFixed(digits)} kW`;
}

export function fmtPct(p: number, digits = 1): string {
  return `${(p * 100).toFixed(digits)}%`;
}

export function fmtPctNum(p: number, digits = 1): string {
  return `${p.toFixed(digits)}%`;
}

export function fmtNum(n: number, digits = 0): string {
  return n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

export function fmtCarbon(kg: number): string {
  if (kg >= 1_000_000) return `${(kg / 1_000_000).toFixed(2)} kt`;
  if (kg >= 1_000) return `${(kg / 1_000).toFixed(2)} t`;
  return `${kg.toFixed(1)} kg`;
}

export function shortHash(h: string, head = 8, tail = 6): string {
  if (h.length <= head + tail + 3) return h;
  return `${h.slice(0, head)}…${h.slice(-tail)}`;
}

export function timeAgo(iso: string): string {
  const t = new Date(iso).getTime();
  const s = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
