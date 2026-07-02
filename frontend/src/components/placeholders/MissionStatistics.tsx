import type { MissionState } from '@/types/mission';

interface MissionStatisticsProps {
  missionState: MissionState | null;
}

export function MissionStatistics({ missionState }: MissionStatisticsProps) {
  return (
    <div
      data-testid="mission-statistics"
      className="flex flex-col items-center justify-center rounded border border-border-default bg-bg-surface p-4"
    >
      <p className="font-mono text-xs text-text-muted">MISSION STATISTICS</p>
      <p className="mt-1 text-2xs text-text-dim">Phase 6B</p>
      {missionState && (
        <p className="mt-2 font-mono text-xs text-text-secondary">
          {missionState.status}
        </p>
      )}
    </div>
  );
}
