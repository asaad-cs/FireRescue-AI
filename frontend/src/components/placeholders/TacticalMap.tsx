import type { DroneState, ZoneState } from '@/types/mission';

interface TacticalMapProps {
  zoneStates: Record<string, ZoneState>;
  droneState: DroneState | null;
  exploredPercentage: number;
  isStale: boolean;
}

export function TacticalMap({ zoneStates, droneState, exploredPercentage, isStale }: TacticalMapProps) {
  const zoneCount = Object.keys(zoneStates).length;

  return (
    <div
      data-testid="tactical-map"
      className="flex h-full flex-col items-center justify-center rounded border border-border-default bg-bg-surface p-4"
    >
      <p className="font-mono text-xs text-text-muted">TACTICAL MAP</p>
      <p className="mt-1 text-2xs text-text-dim">Phase 6B</p>
      {zoneCount > 0 && (
        <p className="mt-2 font-mono text-xs text-text-secondary">
          {zoneCount} zones · {exploredPercentage.toFixed(0)}% explored
        </p>
      )}
      {droneState && (
        <p className="mt-1 font-mono text-xs text-text-secondary">
          Drone ({droneState.x},{droneState.y}) floor {droneState.floor}
        </p>
      )}
      {isStale && (
        <p className="mt-2 font-mono text-xs text-hazard-high-text">STALE DATA</p>
      )}
    </div>
  );
}
