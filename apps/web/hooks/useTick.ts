"use client";

import { useEffect, useRef, useState } from "react";
import type { SimEvent, TickPayload } from "@/types/api";
import { WS_URL } from "@/lib/env";

interface UseTickResult {
  tick: TickPayload | null;
  connected: boolean;
  /** Rolling history of recent ticks, capped. */
  history: TickPayload[];
}

export function useTick(historyCap = 120): UseTickResult {
  const [tick, setTick] = useState<TickPayload | null>(null);
  const [connected, setConnected] = useState(false);
  const [history, setHistory] = useState<TickPayload[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const cancelled = useRef(false);

  useEffect(() => {
    cancelled.current = false;

    const connect = () => {
      if (cancelled.current) return;
      const ws = new WebSocket(WS_URL);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        retryRef.current = 0;
      };
      ws.onclose = () => {
        setConnected(false);
        if (cancelled.current) return;
        const backoff = Math.min(15000, 500 * Math.pow(2, retryRef.current++));
        setTimeout(connect, backoff);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (ev) => {
        let parsed: SimEvent;
        try {
          const text =
            typeof ev.data === "string"
              ? ev.data
              : new TextDecoder().decode(ev.data as ArrayBuffer);
          parsed = JSON.parse(text);
        } catch {
          return;
        }
        if (parsed.type === "tick") {
          setTick(parsed.payload);
          setHistory((h) => {
            const next = [...h, parsed.payload];
            return next.length > historyCap ? next.slice(next.length - historyCap) : next;
          });
        }
      };
    };

    connect();
    return () => {
      cancelled.current = true;
      wsRef.current?.close();
    };
  }, [historyCap]);

  return { tick, connected, history };
}
