import { useEffect, useRef, useState, useCallback } from 'react';
import { api } from './api';

export interface WSEvent {
  type: string;
  [key: string]: unknown;
}

export function useWebSocket(maxEvents = 50) {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const connect = useCallback(async () => {
    try {
      const { ticket } = await api.wsTicket();
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${proto}//${window.location.host}/ws/events?ticket=${ticket}`);

      ws.onopen = () => setConnected(true);

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as WSEvent;
          if (data.type === 'pong') return;
          setEvents((prev) => [data, ...prev].slice(0, maxEvents));
        } catch { /* ignore malformed */ }
      };

      ws.onclose = () => {
        setConnected(false);
        reconnectTimer.current = setTimeout(connect, 5000);
      };

      wsRef.current = ws;
    } catch {
      reconnectTimer.current = setTimeout(connect, 5000);
    }
  }, [maxEvents]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { events, connected };
}
