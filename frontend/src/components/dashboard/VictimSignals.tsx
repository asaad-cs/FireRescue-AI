/**
 * VictimSignals — zones above the victim detection threshold.
 *
 * Detection threshold: victim_probability >= 0.30
 * Alert threshold (amber): >= 0.60
 * Critical threshold (red): >= 0.80
 *
 * Language: "Victim Signal" — never "Victim Confirmed" or "Victim Detected".
 * The system estimates probability; labels must not imply certainty.
 */

import { type ZoneState } from '@/types/mission';
import { formatProbability, formatRelative } from '@/utils/format';

// ── Probability styling ───────────────────────────────────────────────────────

function probColor(p: number): string {
  if (p >= 0.8) return '#ef4444'; // red
  if (p >= 0.6) return '#f59e0b'; // amber
  return '#8097b0';               // muted — below alert threshold
}

function probLabel(p: number): string {
  if (p >= 0.8) return 'HIGH';
  if (p >= 0.6) return 'ELEVATED';
  return 'LOW';
}

// ── Signal entry ──────────────────────────────────────────────────────────────

interface SignalEntryProps {
  zone: ZoneState;
}

function SignalEntry({ zone }: SignalEntryProps) {
  const color = probColor(zone.victim_probability);
  const pct = zone.victim_probability * 100;

  return (
    <div
      data-testid={`victim-signal-${zone.zone_id}`}
      role="listitem"
      aria-label={`Victim signal in zone ${zone.label} — ${formatProbability(zone.victim_probability)} probability`}
      className="flex flex-col gap-1 rounded border border-border-subtle bg-bg-raised p-2"
    >
      {/* Zone label + probability + level */}
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs font-bold text-text-primary">
          {zone.label}
        </span>
        <span
          className="font-mono text-2xs font-semibold"
          style={{ color }}
        >
          {formatProbability(zone.victim_probability)}
        </span>
        <span
          className="rounded px-1 py-0.5 font-mono text-[0.5rem] font-bold"
          style={{
            color,
            backgroundColor: `${color}1a`,
            border: `1px solid ${color}33`,
          }}
        >
          {probLabel(zone.victim_probability)}
        </span>
        {zone.last_observed_at && (
          <span className="ml-auto font-mono text-2xs text-text-dim">
            {formatRelative(zone.last_observed_at)}
          </span>
        )}
      </div>

      {/* Probability bar */}
      <div
        className="h-2 w-full overflow-hidden rounded-full"
        style={{ backgroundColor: '#1a2435' }}
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

// ── Root component ────────────────────────────────────────────────────────────

interface VictimSignalsProps {
  zoneStates: Record<string, ZoneState>;
  victimSignalCount: number;
}

const DETECTION_THRESHOLD = 0.3;

export function VictimSignals({ zoneStates, victimSignalCount }: VictimSignalsProps) {
  const signalZones = Object.values(zoneStates)
    .filter((z) => z.victim_probability >= DETECTION_THRESHOLD)
    .sort((a, b) => b.victim_probability - a.victim_probability);

  return (
    <div
      data-testid="victim-signals"
      className="flex flex-col rounded border border-border-default bg-bg-surface"
    >
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-border-subtle px-3 py-2">
        <span className="font-mono text-xs font-semibold text-text-primary">
          VICTIM SIGNALS
        </span>
        {victimSignalCount > 0 && (
          <span className="font-mono text-2xs font-semibold text-hazard-high-text">
            {victimSignalCount} detected
          </span>
        )}
      </div>

      {/* Signal list */}
      <div
        role="list"
        aria-label="Victim signal detections"
        className="flex flex-1 flex-col gap-1.5 overflow-y-auto p-2"
      >
        {signalZones.length === 0 ? (
          <div className="flex flex-1 items-center justify-center py-4">
            <span className="font-mono text-2xs text-text-dim">
              No signals above threshold
            </span>
          </div>
        ) : (
          signalZones.map((zone) => (
            <SignalEntry key={zone.zone_id} zone={zone} />
          ))
        )}
      </div>
    </div>
  );
}
