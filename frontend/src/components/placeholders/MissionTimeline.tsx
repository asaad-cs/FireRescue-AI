import type { Alert, MissionStatus } from '@/types/mission';

interface MissionTimelineProps {
  alerts: Alert[];
  status: MissionStatus;
}

export function MissionTimeline({ alerts, status }: MissionTimelineProps) {
  return (
    <div
      data-testid="mission-timeline"
      className="flex h-full items-center gap-4 overflow-x-auto px-4"
    >
      <span className="shrink-0 font-mono text-xs font-semibold text-text-muted">
        MISSION TIMELINE
      </span>
      <span className="shrink-0 text-2xs text-text-dim">Phase 6B</span>
      <span className="shrink-0 font-mono text-xs text-text-secondary">
        {status} · {alerts.length} event{alerts.length !== 1 ? 's' : ''}
      </span>
    </div>
  );
}
