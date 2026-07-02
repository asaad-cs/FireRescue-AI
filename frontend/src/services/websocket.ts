/**
 * WebSocket service — manages the single persistent connection to the backend.
 *
 * Responsibilities:
 *   - Connect to ws://[host]/ws
 *   - Auto-reconnect with exponential backoff (1s → 2s → 4s → 8s → 16s cap)
 *   - Validate incoming JSON payloads before forwarding
 *   - Emit typed MissionState updates via onMessage callback
 *   - Emit connection status changes via onStatus callback
 *   - Never poll — only push-based communication
 *
 * The service is a plain class; the React hook (useWebSocket) manages its
 * lifecycle (mount = connect, unmount = disconnect).
 */

import { isMissionState, type MissionState } from '@/types/mission';

export type WsStatus = 'connected' | 'disconnected' | 'reconnecting';

export interface WebSocketServiceConfig {
  url: string;
  onMessage: (state: MissionState) => void;
  onStatus: (status: WsStatus) => void;
}

const INITIAL_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 16_000;

export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = INITIAL_RECONNECT_DELAY_MS;
  private shouldReconnect = false;

  constructor(private readonly config: WebSocketServiceConfig) {}

  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;

    this.shouldReconnect = true;
    this.createSocket();
  }

  disconnect(): void {
    this.shouldReconnect = false;
    this.clearReconnectTimer();

    if (this.ws) {
      this.ws.close(1000, 'Client disconnecting');
      this.ws = null;
    }
  }

  get status(): WsStatus {
    if (!this.ws) return 'disconnected';
    switch (this.ws.readyState) {
      case WebSocket.OPEN:        return 'connected';
      case WebSocket.CONNECTING:  return 'reconnecting';
      default:                    return 'disconnected';
    }
  }

  // ─── Private ───────────────────────────────────────────────────────────────

  private createSocket(): void {
    this.ws = new WebSocket(this.config.url);

    this.ws.onopen = () => {
      this.reconnectDelay = INITIAL_RECONNECT_DELAY_MS;
      this.config.onStatus('connected');
    };

    this.ws.onmessage = (event: MessageEvent) => {
      this.handleMessage(event);
    };

    this.ws.onclose = (event: CloseEvent) => {
      // Normal closure (1000) initiated by disconnect() — do not reconnect
      if (!this.shouldReconnect || event.code === 1000) {
        this.config.onStatus('disconnected');
        return;
      }
      this.config.onStatus('reconnecting');
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      // onerror always fires before onclose; onclose handles reconnect logic
      // Logging only — no user-visible action here
    };
  }

  private handleMessage(event: MessageEvent): void {
    let parsed: unknown;
    try {
      parsed = JSON.parse(event.data as string);
    } catch {
      // Malformed JSON from backend — log and discard; never crash
      console.warn('[WebSocketService] Received non-JSON message:', event.data);
      return;
    }

    if (!isMissionState(parsed)) {
      console.warn('[WebSocketService] Payload does not match MissionState schema:', parsed);
      return;
    }

    this.config.onMessage(parsed);
  }

  private scheduleReconnect(): void {
    this.clearReconnectTimer();
    this.reconnectTimer = setTimeout(() => {
      if (this.shouldReconnect) {
        this.createSocket();
        this.reconnectDelay = Math.min(
          this.reconnectDelay * 2,
          MAX_RECONNECT_DELAY_MS,
        );
      }
    }, this.reconnectDelay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}
