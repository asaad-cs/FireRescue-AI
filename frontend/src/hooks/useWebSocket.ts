/**
 * useWebSocket — React lifecycle bridge for WebSocketService.
 *
 * Responsibilities:
 *   - Create a WebSocketService on mount and destroy it on unmount
 *   - Wire service callbacks to Zustand store actions
 *   - Expose a manual reconnect trigger for the UI
 *
 * Components do not interact with WebSocketService directly.
 * They read state from the Zustand store.
 */

import { useEffect, useRef, useCallback } from 'react';
import { WebSocketService } from '@/services/websocket';
import { useMissionStore } from '@/stores/missionStore';

const WS_URL = '/ws'; // Vite proxy rewrites to ws://localhost:8000/ws in development

export function useWebSocket(): { reconnect: () => void } {
  const setMissionState = useMissionStore((s) => s.setMissionState);
  const setWsStatus = useMissionStore((s) => s.setWsStatus);
  const incrementReconnectAttempts = useMissionStore((s) => s.incrementReconnectAttempts);

  const serviceRef = useRef<WebSocketService | null>(null);

  useEffect(() => {
    const service = new WebSocketService({
      url: WS_URL,
      onMessage: setMissionState,
      onStatus: (status) => {
        setWsStatus(status);
        if (status === 'reconnecting') {
          incrementReconnectAttempts();
        }
      },
    });

    serviceRef.current = service;
    service.connect();

    return () => {
      service.disconnect();
      serviceRef.current = null;
    };
    // Store actions are stable references — no deps needed
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const reconnect = useCallback(() => {
    if (serviceRef.current) {
      serviceRef.current.disconnect();
      serviceRef.current.connect();
    }
  }, []);

  return { reconnect };
}
