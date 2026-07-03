/**
 * AlertPanel — real-time alert display with level-based sorting.
 *
 * Sort order:
 *   1. EMERGENCY (always pinned at top, acked or not)
 *   2. CRITICAL — unacknowledged
 *   3. WARNING
 *   4. INFO
 *   5. CRITICAL — acknowledged (dimmed, at bottom)
 *
 * CRITICAL and EMERGENCY alerts show an ACK button.
 * Acknowledged EMERGENCY alerts stay pinned but lose visual urgency.
 */

import { AlertLevel, AlertType, type Alert } from '@/types/mission';
import { formatRelative } from '@/utils/format';

// ── Styles ────────────────────────────────────────────────────────────────────

const LEVEL_STYLE: Record<
  AlertLevel,
  { bg: string; border: string; text: string; badge: string }
> = {
  [AlertLevel.INFO]: {
    bg: '#071828',
    border: '#1e4d7a',
    text: '#60a5fa',
    badge: '#1e4d7a',
  },
  [AlertLevel.WARNING]: {
    bg: '#1e1200',
    border: '#7a4d00',
    text: '#fbbf24',
    badge: '#7a4d00',
  },
  [AlertLevel.CRITICAL]: {
    bg: '#200808',
    border: '#7a1818',
    text: '#f87171',
    badge: '#7a1818',
  },
  [AlertLevel.EMERGENCY]: {
    bg: '#2a0000',
    border: '#cc0000',
    text: '#ffffff',
    badge: '#cc0000',
  },
};

const ALERT_TYPE_LABEL: Record<AlertType, string> = {
  [AlertType.HAZARD_ELEVATED]: 'HAZARD',
  [AlertType.VICTIM_DETECTED]: 'VICTIM SIGNAL',
  [AlertType.SYSTEM]:          'SYSTEM',
};

// ── Sort ──────────────────────────────────────────────────────────────────────

function alertPriority(alert: Alert, acked: boolean): number {
  // Lower number = higher priority (shown first)
  if (alert.level === AlertLevel.EMERGENCY)                        return 0;
  if (alert.level === AlertLevel.CRITICAL && !acked)               return 1;
  if (alert.level === AlertLevel.WARNING)                          return 2;
  if (alert.level === AlertLevel.INFO)                             return 3;
  if (alert.level === AlertLevel.CRITICAL && acked)                return 4;
  return 5;
}

function sortAlerts(alerts: Alert[], ackedIds: Set<string>): Alert[] {
  return [...alerts].sort((a, b) => {
    const pa = alertPriority(a, ackedIds.has(a.alert_id));
    const pb = alertPriority(b, ackedIds.has(b.alert_id));
    if (pa !== pb) return pa - pb;
    // Same priority: most recent first
    return new Date(b.triggered_at).getTime() - new Date(a.triggered_at).getTime();
  });
}

// ── Alert item ────────────────────────────────────────────────────────────────

interface AlertItemProps {
  alert: Alert;
  isAcknowledged: boolean;
  onAcknowledge: (alertId: string) => void;
}

function AlertItem({ alert, isAcknowledged, onAcknowledge }: AlertItemProps) {
  const style = LEVEL_STYLE[alert.level];
  const needsAck =
    (alert.level === AlertLevel.CRITICAL || alert.level === AlertLevel.EMERGENCY) &&
    !isAcknowledged;

  return (
    <div
      data-testid={`alert-item-${alert.alert_id}`}
      role="listitem"
      aria-label={`${alert.level} alert: ${alert.message}`}
      style={{
        backgroundColor: isAcknowledged ? '#0a0f18' : style.bg,
        borderColor: isAcknowledged ? '#1a2435' : style.border,
        opacity: isAcknowledged && alert.level !== AlertLevel.EMERGENCY ? 0.55 : 1,
        boxShadow: isAcknowledged
          ? 'inset 3px 0 0 #1a2435'
          : `inset 3px 0 0 ${style.badge}, 0 1px 4px #00000066`,
      }}
      className={`flex flex-col gap-1 rounded-md border p-2.5 transition-opacity duration-300${
        alert.level === AlertLevel.EMERGENCY && !isAcknowledged
          ? ' animate-emergency-pulse'
          : ''
      }`}
    >
      {/* Row 1: level badge + zone + timestamp */}
      <div className="flex items-center gap-2">
        <span
          style={{
            backgroundColor: isAcknowledged ? '#1a2435' : style.badge,
            color: isAcknowledged ? '#445566' : style.text,
          }}
          className="shrink-0 rounded px-1.5 py-0.5 font-mono text-[0.55rem] font-bold"
        >
          {alert.level}
        </span>
        <span className="font-mono text-2xs text-text-muted">
          {ALERT_TYPE_LABEL[alert.alert_type]}
        </span>
        <span className="font-mono text-2xs text-text-muted">
          Zone {alert.zone_id}
        </span>
        <span className="ml-auto font-mono text-2xs text-text-dim" title={alert.triggered_at}>
          {formatRelative(alert.triggered_at)}
        </span>
      </div>

      {/* Row 2: message */}
      <p
        style={{ color: isAcknowledged ? '#445566' : style.text }}
        className="font-mono text-2xs leading-snug"
      >
        {alert.message}
      </p>

      {/* Row 3: ACK button for CRITICAL / EMERGENCY */}
      {needsAck && (
        <div className="flex justify-end">
          <button
            data-testid={`ack-alert-${alert.alert_id}`}
            onClick={() => onAcknowledge(alert.alert_id)}
            className="rounded border border-border-strong px-2 py-0.5 font-mono text-2xs text-text-secondary hover:border-text-secondary hover:text-text-primary focus:outline-none focus:ring-1 focus:ring-border-strong"
            aria-label={`Acknowledge ${alert.level} alert`}
          >
            ACKNOWLEDGE
          </button>
        </div>
      )}
    </div>
  );
}

// ── Root component ────────────────────────────────────────────────────────────

interface AlertPanelProps {
  alerts: Alert[];
  alertCount: number;
  acknowledgedAlertIds: string[];
  onAcknowledge: (alertId: string) => void;
}

export function AlertPanel({
  alerts,
  alertCount,
  acknowledgedAlertIds,
  onAcknowledge,
}: AlertPanelProps) {
  const ackedSet = new Set(acknowledgedAlertIds);
  const sorted = sortAlerts(alerts, ackedSet);
  const unacknowledgedCount = alerts.filter(
    (a) =>
      (a.level === AlertLevel.CRITICAL || a.level === AlertLevel.EMERGENCY) &&
      !ackedSet.has(a.alert_id),
  ).length;

  return (
    <div
      data-testid="alert-panel"
      className="flex h-full flex-col rounded border border-border-default bg-bg-surface"
    >
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-border-subtle px-3 py-2">
        <span className="font-mono text-xs font-semibold text-text-primary">
          ALERTS
        </span>
        <div className="flex items-center gap-2">
          {unacknowledgedCount > 0 && (
            <span className="rounded bg-alert-emergency-bg px-1.5 font-mono text-2xs font-bold text-alert-emergency-text">
              {unacknowledgedCount} UNACK
            </span>
          )}
          <span className="font-mono text-2xs text-text-muted">
            {alertCount} total
          </span>
        </div>
      </div>

      {/* Alert list */}
      <div
        role="list"
        aria-label="Active alerts"
        className="flex flex-1 flex-col gap-1.5 overflow-y-auto p-2"
      >
        {sorted.length === 0 ? (
          <div className="flex flex-1 items-center justify-center">
            <span className="font-mono text-2xs text-text-dim">No active alerts</span>
          </div>
        ) : (
          sorted.map((alert) => (
            <AlertItem
              key={alert.alert_id}
              alert={alert}
              isAcknowledged={ackedSet.has(alert.alert_id)}
              onAcknowledge={onAcknowledge}
            />
          ))
        )}
      </div>
    </div>
  );
}
