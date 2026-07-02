import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WebSocketService } from '@/services/websocket';
import type { WsStatus } from '@/services/websocket';
import {
  MissionStatus,
  HazardLevel,
  ConnectionStatus,
  type MissionState,
} from '@/types/mission';

// ─── Mock WebSocket ───────────────────────────────────────────────────────────

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  readyState: number = WebSocket.CONNECTING;

  constructor(public readonly url: string) {
    MockWebSocket.instances.push(this);
  }

  send = vi.fn();

  close(code?: number) {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code: code ?? 1000 }));
  }

  // Helpers to simulate events from the server
  triggerOpen() {
    this.readyState = WebSocket.OPEN;
    this.onopen?.(new Event('open'));
  }

  triggerMessage(data: unknown) {
    this.onmessage?.(
      new MessageEvent('message', { data: JSON.stringify(data) }),
    );
  }

  triggerRawMessage(raw: string) {
    this.onmessage?.(new MessageEvent('message', { data: raw }));
  }

  triggerError() {
    this.onerror?.(new Event('error'));
    this.close(1006);
  }

  triggerUnexpectedClose() {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code: 1006 }));
  }
}

// ─── Minimal valid MissionState ───────────────────────────────────────────────

const VALID_STATE: MissionState = {
  mission_id: 'test-001',
  status: MissionStatus.IDLE,
  started_at: null,
  ended_at: null,
  elapsed_seconds: 0,
  drone_state: null,
  zone_states: {},
  active_alerts: [],
  latest_readings: { temperature: null, co_level: null, smoke_density: null },
  alert_count: 0,
  victim_signal_count: 0,
  explored_percentage: 0,
  connection_status: ConnectionStatus.DISCONNECTED,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any;

// ─── Setup ────────────────────────────────────────────────────────────────────

beforeEach(() => {
  MockWebSocket.instances = [];
  vi.stubGlobal('WebSocket', MockWebSocket);
  vi.useFakeTimers();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function latestSocket(): MockWebSocket {
  return MockWebSocket.instances[MockWebSocket.instances.length - 1];
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('WebSocketService — connection lifecycle', () => {
  it('creates a WebSocket with the configured URL', () => {
    const service = new WebSocketService({
      url: 'ws://test/ws',
      onMessage: vi.fn(),
      onStatus: vi.fn(),
    });
    service.connect();
    expect(MockWebSocket.instances).toHaveLength(1);
    expect(latestSocket().url).toBe('ws://test/ws');
  });

  it('calls onStatus("connected") when socket opens', () => {
    const onStatus = vi.fn() as (status: WsStatus) => void;
    const service = new WebSocketService({ url: 'ws://x', onMessage: vi.fn(), onStatus });
    service.connect();
    latestSocket().triggerOpen();
    expect(onStatus).toHaveBeenCalledWith('connected');
  });

  it('calls onStatus("disconnected") when disconnected intentionally', () => {
    const onStatus = vi.fn() as (status: WsStatus) => void;
    const service = new WebSocketService({ url: 'ws://x', onMessage: vi.fn(), onStatus });
    service.connect();
    latestSocket().triggerOpen();
    service.disconnect();
    expect(onStatus).toHaveBeenCalledWith('disconnected');
  });

  it('does not reconnect after intentional disconnect', () => {
    const service = new WebSocketService({ url: 'ws://x', onMessage: vi.fn(), onStatus: vi.fn() });
    service.connect();
    latestSocket().triggerOpen();
    service.disconnect();
    vi.advanceTimersByTime(5000);
    // Only 1 socket was ever created
    expect(MockWebSocket.instances).toHaveLength(1);
  });
});

describe('WebSocketService — auto-reconnect', () => {
  it('calls onStatus("reconnecting") on unexpected close', () => {
    const onStatus = vi.fn() as (status: WsStatus) => void;
    const service = new WebSocketService({ url: 'ws://x', onMessage: vi.fn(), onStatus });
    service.connect();
    latestSocket().triggerOpen();
    latestSocket().triggerUnexpectedClose();
    expect(onStatus).toHaveBeenCalledWith('reconnecting');
  });

  it('reconnects after a delay on unexpected close', () => {
    const service = new WebSocketService({ url: 'ws://x', onMessage: vi.fn(), onStatus: vi.fn() });
    service.connect();
    latestSocket().triggerOpen();
    latestSocket().triggerUnexpectedClose();
    expect(MockWebSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(1000);
    expect(MockWebSocket.instances).toHaveLength(2);
  });

  it('doubles the reconnect delay on each failure', () => {
    const service = new WebSocketService({ url: 'ws://x', onMessage: vi.fn(), onStatus: vi.fn() });
    service.connect();

    // First failure → reconnect after 1000 ms
    latestSocket().triggerOpen();
    latestSocket().triggerUnexpectedClose();
    vi.advanceTimersByTime(999);
    expect(MockWebSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(MockWebSocket.instances).toHaveLength(2);

    // Second failure → reconnect after 2000 ms
    latestSocket().triggerUnexpectedClose();
    vi.advanceTimersByTime(1999);
    expect(MockWebSocket.instances).toHaveLength(2);
    vi.advanceTimersByTime(1);
    expect(MockWebSocket.instances).toHaveLength(3);
  });

  it('resets reconnect delay after successful connection', () => {
    const service = new WebSocketService({ url: 'ws://x', onMessage: vi.fn(), onStatus: vi.fn() });
    service.connect();

    // First failure and reconnect
    latestSocket().triggerOpen();
    latestSocket().triggerUnexpectedClose();
    vi.advanceTimersByTime(1000);
    latestSocket().triggerOpen(); // reconnected successfully

    // Third failure should use initial delay again (1000 ms)
    latestSocket().triggerUnexpectedClose();
    vi.advanceTimersByTime(999);
    expect(MockWebSocket.instances).toHaveLength(2);
    vi.advanceTimersByTime(1);
    expect(MockWebSocket.instances).toHaveLength(3);
  });
});

describe('WebSocketService — message handling', () => {
  it('calls onMessage with parsed MissionState for valid payload', () => {
    const onMessage = vi.fn();
    const service = new WebSocketService({ url: 'ws://x', onMessage, onStatus: vi.fn() });
    service.connect();
    latestSocket().triggerOpen();
    latestSocket().triggerMessage(VALID_STATE);
    expect(onMessage).toHaveBeenCalledWith(VALID_STATE);
  });

  it('does not call onMessage for malformed JSON', () => {
    const onMessage = vi.fn();
    const service = new WebSocketService({ url: 'ws://x', onMessage, onStatus: vi.fn() });
    service.connect();
    latestSocket().triggerOpen();
    latestSocket().triggerRawMessage('{not valid json}');
    expect(onMessage).not.toHaveBeenCalled();
  });

  it('does not call onMessage for valid JSON that lacks required fields', () => {
    const onMessage = vi.fn();
    const service = new WebSocketService({ url: 'ws://x', onMessage, onStatus: vi.fn() });
    service.connect();
    latestSocket().triggerOpen();
    latestSocket().triggerMessage({ some: 'random', object: true });
    expect(onMessage).not.toHaveBeenCalled();
  });

  it('does not call onMessage for null payload', () => {
    const onMessage = vi.fn();
    const service = new WebSocketService({ url: 'ws://x', onMessage, onStatus: vi.fn() });
    service.connect();
    latestSocket().triggerOpen();
    latestSocket().triggerMessage(null);
    expect(onMessage).not.toHaveBeenCalled();
  });

  it('does not throw on malformed JSON — mission continues', () => {
    const service = new WebSocketService({ url: 'ws://x', onMessage: vi.fn(), onStatus: vi.fn() });
    service.connect();
    latestSocket().triggerOpen();
    expect(() => latestSocket().triggerRawMessage('BOOM')).not.toThrow();
  });
});

describe('WebSocketService — concurrent connect guard', () => {
  it('does not create a second socket if already open', () => {
    const service = new WebSocketService({ url: 'ws://x', onMessage: vi.fn(), onStatus: vi.fn() });
    service.connect();
    latestSocket().triggerOpen();
    service.connect(); // second call while open
    expect(MockWebSocket.instances).toHaveLength(1);
  });
});

describe('WebSocketService — hazard level coverage', () => {
  it('delivers all HazardLevel values without filtering', () => {
    const onMessage = vi.fn();
    const service = new WebSocketService({ url: 'ws://x', onMessage, onStatus: vi.fn() });
    service.connect();
    latestSocket().triggerOpen();

    for (const level of Object.values(HazardLevel)) {
      const state = {
        ...VALID_STATE,
        zone_states: {
          z1: {
            zone_id: 'z1',
            label: 'Z1',
            grid_x: 0,
            grid_y: 0,
            hazard_level: level,
            victim_probability: 0,
            last_observed_at: null,
          },
        },
      };
      latestSocket().triggerMessage(state);
    }

    expect(onMessage).toHaveBeenCalledTimes(Object.values(HazardLevel).length);
  });
});
