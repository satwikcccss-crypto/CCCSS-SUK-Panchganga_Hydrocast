// frontend/hooks/useWebSocket.ts
"use client";
import { useEffect, useRef, useState } from "react";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/live";
const MAX_RETRIES = 20;
const BASE_DELAY_MS = 5000;
const MAX_DELAY_MS = 60000;

export function useWebSocket() {
  const ws  = useRef<WebSocket | null>(null);
  const [lastEvent, setLastEvent] = useState<any>(null);
  const [connected, setConnected]  = useState(false);
  const retryCount = useRef(0);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function connect() {
      if (retryCount.current >= MAX_RETRIES) {
        console.warn(`[WS] Max reconnect attempts (${MAX_RETRIES}) reached. Giving up.`);
        return;
      }

      ws.current = new WebSocket(WS_URL);

      ws.current.onopen = () => {
        setConnected(true);
        retryCount.current = 0;  // Reset on successful connection
      };

      ws.current.onclose = () => {
        setConnected(false);
        retryCount.current += 1;
        // Exponential backoff: 5s, 10s, 20s, 40s, ... capped at 60s
        const delay = Math.min(MAX_DELAY_MS, BASE_DELAY_MS * Math.pow(2, retryCount.current - 1));
        console.info(`[WS] Connection closed. Reconnecting in ${delay / 1000}s (attempt ${retryCount.current}/${MAX_RETRIES})`);
        retryTimer.current = setTimeout(connect, delay);
      };

      ws.current.onmessage = (e) => {
        try { setLastEvent(JSON.parse(e.data)); }
        catch {}
      };
    }

    connect();

    return () => {
      if (retryTimer.current) clearTimeout(retryTimer.current);
      ws.current?.close();
    };
  }, []);

  return { lastEvent, connected };
}
