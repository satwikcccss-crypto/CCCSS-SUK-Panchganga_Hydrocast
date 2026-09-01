// frontend/hooks/useWebSocket.ts
"use client";
import { useEffect, useRef, useState } from "react";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/live";

export function useWebSocket() {
  const ws  = useRef<WebSocket | null>(null);
  const [lastEvent, setLastEvent] = useState<any>(null);
  const [connected, setConnected]  = useState(false);

  useEffect(() => {
    function connect() {
      ws.current = new WebSocket(WS_URL);
      ws.current.onopen  = () => setConnected(true);
      ws.current.onclose = () => {
        setConnected(false);
        setTimeout(connect, 5000);   // auto-reconnect
      };
      ws.current.onmessage = (e) => {
        try { setLastEvent(JSON.parse(e.data)); }
        catch {}
      };
    }
    connect();
    return () => ws.current?.close();
  }, []);

  return { lastEvent, connected };
}
