import { useState, useEffect, useRef, useCallback } from 'react';
import type { ContestInfo } from '@/types';
import { fetchContestInfo, buildWsUrl } from '@/api';

export function useContestInfo() {
  const [info, setInfo] = useState<ContestInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await fetchContestInfo();
      setInfo(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка загрузки');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return { info, error, loading, reload: load };
}

export function useWebSocket(
  onMessage: (msg: unknown) => void,
  onOpen?: () => void,
) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  const connect = useCallback(() => {
    const ws = new WebSocket(buildWsUrl());

    ws.onopen = () => {
      onOpen?.();
      pingInterval.current = setInterval(() => {
        ws.send(JSON.stringify({ type: 'ping' }));
      }, 25_000);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string);
        onMessage(data);
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      if (pingInterval.current) clearInterval(pingInterval.current);
      reconnectTimeout.current = setTimeout(() => { void connect(); }, 3_000);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [onMessage, onOpen]);

  useEffect(() => {
    void connect();
    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (pingInterval.current) clearInterval(pingInterval.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return wsRef;
}
