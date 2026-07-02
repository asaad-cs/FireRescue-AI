/**
 * ConnectionBanner — full-width warning strip shown when WebSocket is not
 * connected. Displayed above the main content area.
 *
 * States:
 *   reconnecting  → shows attempt count and "Reconnecting…" message
 *   disconnected  → shows "Backend offline" with a manual reconnect button
 *
 * Hidden entirely when wsStatus === 'connected'.
 */

import type { WsStatus } from '@/services/websocket';

interface ConnectionBannerProps {
  wsStatus: WsStatus;
  reconnectAttempts: number;
  onReconnect: () => void;
}

export function ConnectionBanner({
  wsStatus,
  reconnectAttempts,
  onReconnect,
}: ConnectionBannerProps) {
  if (wsStatus === 'connected') return null;

  const isReconnecting = wsStatus === 'reconnecting';

  return (
    <div
      data-testid="connection-banner"
      role="alert"
      aria-live="assertive"
      className="flex shrink-0 items-center justify-center gap-3 border-b border-alert-emergency-border bg-alert-emergency-bg px-4 py-1.5"
    >
      {/* Status dot */}
      <span
        aria-hidden="true"
        className={`h-2 w-2 rounded-full bg-alert-emergency-border${isReconnecting ? ' animate-reconnect-blink' : ''}`}
      />

      {/* Message */}
      <span className="font-mono text-xs font-semibold text-alert-emergency-text">
        {isReconnecting
          ? `RECONNECTING — Attempt ${reconnectAttempts}`
          : 'BACKEND OFFLINE — Live data unavailable'}
      </span>

      {/* Manual reconnect button (only when fully disconnected) */}
      {!isReconnecting && (
        <button
          data-testid="reconnect-btn"
          onClick={onReconnect}
          className="rounded border border-alert-emergency-border px-2.5 py-0.5 font-mono text-2xs font-semibold text-alert-emergency-text hover:bg-alert-emergency-border/20 focus:outline-none focus:ring-1 focus:ring-alert-emergency-border"
          aria-label="Manually reconnect to backend"
        >
          RECONNECT
        </button>
      )}
    </div>
  );
}
