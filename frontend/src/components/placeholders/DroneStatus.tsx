import type { DroneState, LatestReadings } from '@/types/mission';

interface DroneStatusProps {
  droneState: DroneState | null;
  latestReadings: LatestReadings;
  isStale: boolean;
}

export function DroneStatus({ droneState, latestReadings, isStale }: DroneStatusProps) {
  return (
    <div
      data-testid="drone-status"
      className="flex flex-col rounded border border-border-default bg-bg-surface"
    >
      <div className="border-b border-border-subtle px-3 py-2">
        <span className="font-mono text-xs font-semibold text-text-primary">DRONE STATUS</span>
        {isStale && (
          <span className="ml-2 font-mono text-2xs text-hazard-high-text">(STALE)</span>
        )}
      </div>
      <div className="flex flex-1 flex-col items-center justify-center p-4">
        <p className="text-2xs text-text-muted">Phase 6B</p>
        {droneState ? (
          <p className="mt-1 font-mono text-xs text-text-secondary">
            ({droneState.x},{droneState.y}) f{droneState.floor}
          </p>
        ) : (
          <p className="mt-1 text-xs text-text-dim">—</p>
        )}
        {latestReadings.temperature !== null && (
          <p className="mt-1 font-mono text-xs text-text-secondary">
            {latestReadings.temperature.toFixed(1)}°C
          </p>
        )}
      </div>
    </div>
  );
}
