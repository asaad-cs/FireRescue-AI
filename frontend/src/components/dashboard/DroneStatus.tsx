/**
 * DroneStatus — current drone position and live sensor readings.
 *
 * Shows:
 *   - Current zone label and grid coordinates
 *   - Last seen timestamp
 *   - Three sensor bars: temperature, CO level, smoke density
 *   - Stale data indicator when connection is lost or mission paused
 */

import { type DroneState, type LatestReadings, type ZoneState } from '@/types/mission';
import { formatTimestamp, formatRelative } from '@/utils/format';

// ── Sensor bar ────────────────────────────────────────────────────────────────

interface SensorBarProps {
  label: string;
  value: number | null;
  display: string;
  pct: number;
  level: 'normal' | 'warning' | 'danger';
}

const BAR_COLOR: Record<SensorBarProps['level'], string> = {
  normal:  '#4ade80',
  warning: '#f59e0b',
  danger:  '#ef4444',
};

function SensorBar({ label, value, display, pct, level }: SensorBarProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center justify-between">
        <span className="font-mono text-2xs text-text-muted">{label}</span>
        <span
          className="font-mono text-2xs font-semibold"
          style={{ color: value === null ? '#445566' : BAR_COLOR[level] }}
        >
          {display}
        </span>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded-full"
        style={{ backgroundColor: '#1a2435' }}
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label}: ${display}`}
      >
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${pct}%`,
            backgroundColor: value === null ? '#1a2435' : BAR_COLOR[level],
          }}
        />
      </div>
    </div>
  );
}

// ── Sensor level helpers ──────────────────────────────────────────────────────

function tempLevel(v: number): SensorBarProps['level'] {
  if (v >= 100) return 'danger';
  if (v >= 70)  return 'warning';
  return 'normal';
}

function coLevel(v: number): SensorBarProps['level'] {
  if (v >= 500) return 'danger';
  if (v >= 250) return 'warning';
  return 'normal';
}

function smokeLevel(v: number): SensorBarProps['level'] {
  if (v >= 0.75) return 'danger';
  if (v >= 0.55) return 'warning';
  return 'normal';
}

// ── Root component ────────────────────────────────────────────────────────────

interface DroneStatusProps {
  droneState: DroneState | null;
  latestReadings: LatestReadings;
  zoneStates: Record<string, ZoneState>;
  isStale: boolean;
}

export function DroneStatus({
  droneState,
  latestReadings,
  zoneStates,
  isStale,
}: DroneStatusProps) {
  // Look up zone label from drone position
  const droneZone = droneState
    ? zoneStates[`${droneState.x}_${droneState.y}_${droneState.floor}`] ?? null
    : null;
  const zoneLabel = droneZone?.label ?? (droneState ? `(${droneState.x},${droneState.y})` : '—');

  const { temperature, co_level, smoke_density } = latestReadings;

  const tempPct = temperature !== null ? Math.min(100, (temperature / 300) * 100) : 0;
  const coPct   = co_level     !== null ? Math.min(100, (co_level / 1000) * 100)   : 0;
  const smkPct  = smoke_density !== null ? smoke_density * 100                      : 0;

  return (
    <div
      data-testid="drone-status"
      className="flex flex-col rounded border border-border-default bg-bg-surface"
    >
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-border-subtle px-3 py-2">
        <span className="font-mono text-xs font-semibold text-text-primary">
          DRONE STATUS
        </span>
        {isStale && (
          <span className="font-mono text-2xs font-semibold text-hazard-high-text">
            STALE
          </span>
        )}
      </div>

      <div className="flex flex-col gap-2 p-2">
        {/* Position */}
        <div className="flex flex-col gap-0.5 rounded border border-border-subtle bg-bg-raised p-2">
          <div className="flex items-center justify-between">
            <span className="font-mono text-2xs text-text-muted">ZONE</span>
            <span className="font-mono text-xs font-bold text-sky-400">{zoneLabel}</span>
          </div>
          {droneState && (
            <div className="flex items-center justify-between">
              <span className="font-mono text-2xs text-text-muted">GRID</span>
              <span className="font-mono text-2xs text-text-secondary">
                ({droneState.x},{droneState.y}) F{droneState.floor}
              </span>
            </div>
          )}
          {droneState?.last_seen && (
            <div className="flex items-center justify-between">
              <span className="font-mono text-2xs text-text-muted">LAST SEEN</span>
              <span
                className="font-mono text-2xs text-text-secondary"
                title={formatTimestamp(droneState.last_seen)}
              >
                {formatRelative(droneState.last_seen)}
              </span>
            </div>
          )}
          {!droneState && (
            <span className="font-mono text-2xs text-text-dim">No drone data</span>
          )}
        </div>

        {/* Sensor readings */}
        <div className="flex flex-col gap-1.5 rounded border border-border-subtle bg-bg-raised p-2">
          <span className="font-mono text-2xs text-text-muted">SENSOR READINGS</span>
          <SensorBar
            label="TEMP"
            value={temperature}
            display={temperature !== null ? `${temperature.toFixed(1)} °C` : '—'}
            pct={tempPct}
            level={temperature !== null ? tempLevel(temperature) : 'normal'}
          />
          <SensorBar
            label="CO"
            value={co_level}
            display={co_level !== null ? `${co_level.toFixed(1)} ppm` : '—'}
            pct={coPct}
            level={co_level !== null ? coLevel(co_level) : 'normal'}
          />
          <SensorBar
            label="SMOKE"
            value={smoke_density}
            display={smoke_density !== null ? `${(smoke_density * 100).toFixed(1)}%` : '—'}
            pct={smkPct}
            level={smoke_density !== null ? smokeLevel(smoke_density) : 'normal'}
          />
        </div>
      </div>
    </div>
  );
}
