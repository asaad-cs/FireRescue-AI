import { MissionStatus } from '@/types/mission';

interface MissionControlsProps {
  status: MissionStatus;
  missionId: string;
  elapsedSeconds: number;
}

function formatElapsed(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return [h, m, s].map((v) => String(v).padStart(2, '0')).join(':');
}

export function MissionControls({ status, missionId, elapsedSeconds }: MissionControlsProps) {
  return (
    <div data-testid="mission-controls" className="flex items-center gap-3">
      <span className="font-mono text-xs text-text-muted">CONTROLS</span>
      <span className="text-2xs text-text-dim">Phase 6B</span>
      {missionId && (
        <span className="font-mono text-xs text-text-secondary">{missionId}</span>
      )}
      {status !== MissionStatus.IDLE && (
        <span className="font-mono text-xs text-text-secondary">
          {formatElapsed(elapsedSeconds)}
        </span>
      )}
    </div>
  );
}
