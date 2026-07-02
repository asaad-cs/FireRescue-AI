import type { Alert } from '@/types/mission';

interface AlertPanelProps {
  alerts: Alert[];
  alertCount: number;
}

export function AlertPanel({ alerts, alertCount }: AlertPanelProps) {
  return (
    <div
      data-testid="alert-panel"
      className="flex flex-col rounded border border-border-default bg-bg-surface"
    >
      <div className="flex items-center justify-between border-b border-border-subtle px-3 py-2">
        <span className="font-mono text-xs font-semibold text-text-primary">ALERTS</span>
        <span className="font-mono text-xs text-text-secondary">({alertCount})</span>
      </div>
      <div className="flex flex-1 flex-col items-center justify-center p-4">
        <p className="text-2xs text-text-muted">Phase 6B</p>
        {alerts.length === 0 && (
          <p className="mt-1 text-xs text-text-dim">No alerts.</p>
        )}
        {alerts.length > 0 && (
          <p className="mt-1 font-mono text-xs text-text-secondary">
            {alerts.length} alert{alerts.length !== 1 ? 's' : ''} pending
          </p>
        )}
      </div>
    </div>
  );
}
