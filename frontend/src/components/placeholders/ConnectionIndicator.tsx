import type { WsStatus } from '@/services/websocket';

interface ConnectionIndicatorProps {
  wsStatus: WsStatus;
  reconnectAttempts: number;
}

const STATUS_DOT_CLASS: Record<WsStatus, string> = {
  connected:    'bg-status-active',
  disconnected: 'bg-status-idle',
  reconnecting: 'bg-status-connecting',
};

const STATUS_LABEL: Record<WsStatus, string> = {
  connected:    'CONNECTED',
  disconnected: 'DISCONNECTED',
  reconnecting: 'RECONNECTING',
};

export function ConnectionIndicator({ wsStatus, reconnectAttempts }: ConnectionIndicatorProps) {
  return (
    <div
      data-testid="connection-indicator"
      className="flex items-center gap-2"
      role="status"
      aria-label={`WebSocket ${STATUS_LABEL[wsStatus]}`}
    >
      <span
        className={`h-2 w-2 rounded-full ${STATUS_DOT_CLASS[wsStatus]}${
          wsStatus === 'connected' ? ' animate-status-active' : ''
        }${wsStatus === 'reconnecting' ? ' animate-reconnect-blink' : ''}`}
        aria-hidden="true"
      />
      <span className="font-mono text-xs text-text-secondary">
        {STATUS_LABEL[wsStatus]}
      </span>
      {wsStatus === 'reconnecting' && reconnectAttempts > 0 && (
        <span className="font-mono text-2xs text-text-muted">
          #{reconnectAttempts}
        </span>
      )}
    </div>
  );
}
