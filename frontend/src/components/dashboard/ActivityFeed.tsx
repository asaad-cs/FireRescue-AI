/**
 * ActivityFeed — compact chronological log of recent operational events.
 *
 * Events are derived directly from active_alerts (newest first).
 * A connection status line is prepended when the WebSocket is not connected.
 *
 * Displays at most MAX_EVENTS entries. No separate event store needed.
 */

import { AlertLevel, AlertType, type Alert } from '@/types/mission';
import type { WsStatus } from '@/services/websocket';
import { formatRelative, formatTimestamp } from '@/utils/format';

const MAX_EVENTS = 8;

// ── Event row style ───────────────────────────────────────────────────────────

interface EventRowProps {
  timestamp: string;
  label: string;
  message: string;
  color: string;
}

function EventRow({ timestamp, label, message, color }: EventRowProps) {
  return (
    <div className="flex items-start gap-2 py-1">
      <span
        aria-hidden="true"
        className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full"
        style={{ backgroundColor: color }}
      />
      <span
        className="shrink-0 font-mono text-2xs text-text-muted"
        title={formatTimestamp(timestamp)}
      >
        {formatRelative(timestamp)}
      </span>
      <span
        className="shrink-0 rounded px-1 font-mono text-[0.5rem] font-bold"
        style={{ color, backgroundColor: `${color}1a` }}
      >
        {label}
      </span>
      <span className="min-w-0 truncate font-mono text-2xs text-text-secondary" title={message}>
        {message}
      </span>
    </div>
  );
}

// ── Alert level → colour ──────────────────────────────────────────────────────

const LEVEL_COLOR: Record<AlertLevel, string> = {
  [AlertLevel.INFO]:      '#60a5fa',
  [AlertLevel.WARNING]:   '#fbbf24',
  [AlertLevel.CRITICAL]:  '#f87171',
  [AlertLevel.EMERGENCY]: '#ffffff',
};

const TYPE_LABEL: Record<AlertType, string> = {
  [AlertType.HAZARD_ELEVATED]: 'HAZARD',
  [AlertType.VICTIM_DETECTED]: 'VICTIM',
  [AlertType.SYSTEM]:          'SYSTEM',
};

// ── Root component ────────────────────────────────────────────────────────────

interface ActivityFeedProps {
  alerts: Alert[];
  wsStatus: WsStatus;
}

export function ActivityFeed({ alerts, wsStatus }: ActivityFeedProps) {
  // Sort newest first, take top N
  const recent = [...alerts]
    .sort(
      (a, b) =>
        new Date(b.triggered_at).getTime() - new Date(a.triggered_at).getTime(),
    )
    .slice(0, MAX_EVENTS);

  return (
    <div
      data-testid="activity-feed"
      className="flex flex-col rounded border border-border-default bg-bg-surface"
    >
      {/* Header */}
      <div className="shrink-0 border-b border-border-subtle px-3 py-1.5">
        <span className="font-mono text-2xs font-semibold text-text-muted">
          ACTIVITY
        </span>
      </div>

      <div className="flex flex-col overflow-y-auto px-3 py-1.5">
        {/* Connection event if not connected */}
        {wsStatus !== 'connected' && (
          <EventRow
            timestamp={new Date().toISOString()}
            label={wsStatus === 'reconnecting' ? 'RECONNECT' : 'OFFLINE'}
            message={
              wsStatus === 'reconnecting'
                ? 'Reconnecting to backend…'
                : 'Backend connection lost'
            }
            color="#ef4444"
          />
        )}

        {recent.length === 0 && wsStatus === 'connected' ? (
          <span className="py-1 font-mono text-2xs text-text-dim">
            No events yet
          </span>
        ) : (
          recent.map((alert) => (
            <EventRow
              key={alert.alert_id}
              timestamp={alert.triggered_at}
              label={TYPE_LABEL[alert.alert_type]}
              message={alert.message}
              color={LEVEL_COLOR[alert.level]}
            />
          ))
        )}
      </div>
    </div>
  );
}
