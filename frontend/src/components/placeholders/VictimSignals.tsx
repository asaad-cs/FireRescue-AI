import type { ZoneState } from '@/types/mission';

interface VictimSignalsProps {
  zoneStates: Record<string, ZoneState>;
  victimSignalCount: number;
}

export function VictimSignals({ zoneStates, victimSignalCount }: VictimSignalsProps) {
  const zonesWithSignals = Object.values(zoneStates).filter(
    (z) => z.victim_probability >= 0.3,
  );

  return (
    <div
      data-testid="victim-signals"
      className="flex flex-col rounded border border-border-default bg-bg-surface"
    >
      <div className="flex items-center justify-between border-b border-border-subtle px-3 py-2">
        <span className="font-mono text-xs font-semibold text-text-primary">VICTIM SIGNALS</span>
        {victimSignalCount > 0 && (
          <span className="font-mono text-xs text-hazard-high-text">({victimSignalCount})</span>
        )}
      </div>
      <div className="flex flex-1 flex-col items-center justify-center p-4">
        <p className="text-2xs text-text-muted">Phase 6B</p>
        {zonesWithSignals.length === 0 ? (
          <p className="mt-1 text-xs text-text-dim">No detections above threshold.</p>
        ) : (
          <p className="mt-1 font-mono text-xs text-text-secondary">
            {zonesWithSignals.length} signal{zonesWithSignals.length !== 1 ? 's' : ''} detected
          </p>
        )}
      </div>
    </div>
  );
}
