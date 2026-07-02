/**
 * TacticalMap — CSS Grid map of the building floor plan.
 *
 * Hardcoded 5×4 grid for "Warehouse Alpha". Zones appear as the drone visits
 * them; unvisited cells render as UNOBSERVED. Drone position is highlighted
 * with a ring. Zones with victim_probability ≥ 0.3 show a signal indicator.
 */

import { HazardLevel, type DroneState, type ZoneState } from '@/types/mission';
import { formatPct, formatTimestamp } from '@/utils/format';

// ── Colour palette (inline styles — immune to Tailwind purge) ─────────────────

const HAZARD_STYLE: Record<
  HazardLevel,
  { bg: string; text: string; border: string }
> = {
  [HazardLevel.UNOBSERVED]: { bg: '#0d1520', text: '#2a3f55', border: '#1a2435' },
  [HazardLevel.CLEAR]:      { bg: '#061810', text: '#22c55e', border: '#0d3018' },
  [HazardLevel.LOW]:        { bg: '#0d2a1a', text: '#4ade80', border: '#154520' },
  [HazardLevel.MODERATE]:   { bg: '#2a1c00', text: '#f59e0b', border: '#503600' },
  [HazardLevel.HIGH]:       { bg: '#2e0f00', text: '#f97316', border: '#5c2000' },
  [HazardLevel.CRITICAL]:   { bg: '#380a0a', text: '#ef4444', border: '#6e1010' },
};

const HAZARD_ABBR: Record<HazardLevel, string> = {
  [HazardLevel.UNOBSERVED]: '',
  [HazardLevel.CLEAR]:      'CLR',
  [HazardLevel.LOW]:        'LOW',
  [HazardLevel.MODERATE]:   'MOD',
  [HazardLevel.HIGH]:       'HIGH',
  [HazardLevel.CRITICAL]:   'CRIT',
};

const COL_LABELS = ['A', 'B', 'C', 'D', 'E'] as const;
const GRID_COLS = 5;
const GRID_ROWS = 4;
const FLOOR = 1;

// ── Props ─────────────────────────────────────────────────────────────────────

interface TacticalMapProps {
  zoneStates: Record<string, ZoneState>;
  droneState: DroneState | null;
  exploredPercentage: number;
  isStale: boolean;
}

// ── Zone cell ─────────────────────────────────────────────────────────────────

interface ZoneCellProps {
  col: number;
  row: number;
  zone: ZoneState | null;
  hasDrone: boolean;
}

function ZoneCell({ col, row, zone, hasDrone }: ZoneCellProps) {
  const hazard = zone?.hazard_level ?? HazardLevel.UNOBSERVED;
  const style = HAZARD_STYLE[hazard];
  const label = zone?.label ?? `${COL_LABELS[col]}${row + 1}`;
  const hasVictim = (zone?.victim_probability ?? 0) >= 0.3;
  const highVictim = (zone?.victim_probability ?? 0) >= 0.6;

  return (
    <div
      data-testid={`zone-cell-${col}-${row}`}
      aria-label={`Zone ${label} — ${hazard}${hasDrone ? ', drone here' : ''}${hasVictim ? ', victim signal' : ''}`}
      style={{
        backgroundColor: style.bg,
        borderColor: style.border,
        color: style.text,
        outline: hasDrone ? '2px solid #38bdf8' : undefined,
        outlineOffset: hasDrone ? '-2px' : undefined,
      }}
      className="relative flex min-h-[4rem] flex-col items-center justify-center rounded border p-1 text-center"
    >
      {/* Zone label */}
      <span className="font-mono text-xs font-bold leading-none">{label}</span>

      {/* Hazard abbreviation */}
      {hazard !== HazardLevel.UNOBSERVED && (
        <span className="mt-0.5 font-mono text-[0.55rem] leading-none opacity-80">
          {HAZARD_ABBR[hazard]}
        </span>
      )}

      {/* Drone indicator — pulsing ping */}
      {hasDrone && (
        <span aria-hidden="true" className="absolute right-1 top-1" title="Drone">
          <span className="absolute inline-flex h-2.5 w-2.5 animate-drone-ping rounded-full bg-sky-400" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-sky-400" style={{ boxShadow: '0 0 5px #38bdf8' }} />
        </span>
      )}

      {/* Victim signal indicator */}
      {hasVictim && (
        <span
          aria-label="Victim signal"
          className={`absolute bottom-0.5 left-1 font-mono text-[0.6rem] leading-none ${
            highVictim ? 'text-amber-400' : 'text-amber-600'
          }`}
        >
          ⚑
        </span>
      )}
    </div>
  );
}

// ── Legend ────────────────────────────────────────────────────────────────────

function MapLegend() {
  const levels: Array<{ level: HazardLevel; label: string }> = [
    { level: HazardLevel.UNOBSERVED, label: 'Unobserved' },
    { level: HazardLevel.CLEAR,      label: 'Clear' },
    { level: HazardLevel.LOW,        label: 'Low' },
    { level: HazardLevel.MODERATE,   label: 'Moderate' },
    { level: HazardLevel.HIGH,       label: 'High' },
    { level: HazardLevel.CRITICAL,   label: 'Critical' },
  ];

  return (
    <div
      data-testid="map-legend"
      className="flex flex-wrap items-center gap-x-3 gap-y-1 px-1 py-1.5"
    >
      {levels.map(({ level, label }) => (
        <span key={level} className="flex items-center gap-1">
          <span
            aria-hidden="true"
            className="h-2.5 w-2.5 rounded-sm border"
            style={{
              backgroundColor: HAZARD_STYLE[level].bg,
              borderColor: HAZARD_STYLE[level].border,
            }}
          />
          <span className="font-mono text-[0.6rem] text-text-muted">{label}</span>
        </span>
      ))}
      <span className="flex items-center gap-1">
        <span
          aria-hidden="true"
          className="h-2.5 w-2.5 rounded-full bg-sky-400"
          style={{ boxShadow: '0 0 4px #38bdf8' }}
        />
        <span className="font-mono text-[0.6rem] text-text-muted">Drone</span>
      </span>
      <span className="flex items-center gap-1">
        <span className="font-mono text-[0.6rem] text-amber-400">⚑</span>
        <span className="font-mono text-[0.6rem] text-text-muted">Victim Signal</span>
      </span>
    </div>
  );
}

// ── Root component ────────────────────────────────────────────────────────────

export function TacticalMap({
  zoneStates,
  droneState,
  exploredPercentage,
  isStale,
}: TacticalMapProps) {
  // Build position lookup: "col_row" → ZoneState
  const lookup: Record<string, ZoneState> = {};
  for (const z of Object.values(zoneStates)) {
    lookup[`${z.grid_x}_${z.grid_y}`] = z;
  }

  const visitedCount = Object.keys(zoneStates).length;
  const totalCells = GRID_COLS * GRID_ROWS;
  const droneZoneLabel = (() => {
    if (!droneState) return null;
    const z = zoneStates[`${droneState.x}_${droneState.y}_${FLOOR}`];
    return z?.label ?? `(${droneState.x},${droneState.y})`;
  })();
  const droneLastSeen = droneState?.last_seen ?? null;

  return (
    <div
      data-testid="tactical-map"
      className="flex h-full flex-col overflow-hidden rounded border border-border-default bg-bg-surface"
    >
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-border-subtle px-3 py-2">
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs font-semibold text-text-primary">
            BUILDING MAP
          </span>
          <span className="font-mono text-2xs text-text-muted">Floor {FLOOR}</span>
          {isStale && (
            <span className="font-mono text-2xs font-semibold text-hazard-high-text">
              STALE
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <span className="font-mono text-2xs text-text-secondary">
            {visitedCount}/{totalCells} zones · {formatPct(exploredPercentage)} explored
          </span>
          {droneZoneLabel && (
            <span className="font-mono text-2xs text-sky-400">
              Drone → {droneZoneLabel}
              {droneLastSeen && (
                <span className="ml-1 text-text-muted">
                  @ {formatTimestamp(droneLastSeen)}
                </span>
              )}
            </span>
          )}
        </div>
      </div>

      {/* Grid */}
      <div className="min-h-0 flex-1 p-2">
        <div className="flex h-full gap-1">
          {/* Row number labels (1–4) on the left */}
          <div
            className="flex shrink-0 flex-col justify-around"
            style={{ width: '1rem' }}
            aria-hidden="true"
          >
            {Array.from({ length: GRID_ROWS }, (_, row) => (
              <span
                key={row}
                className="flex items-center justify-center font-mono text-[0.5rem] text-text-dim"
              >
                {row + 1}
              </span>
            ))}
          </div>

          {/* Column + grid */}
          <div className="flex flex-1 flex-col gap-1">
            {/* Column letter labels (A–E) on top */}
            <div
              className="flex shrink-0"
              style={{ gap: '4px' }}
              aria-hidden="true"
            >
              {COL_LABELS.map((letter) => (
                <span
                  key={letter}
                  className="flex flex-1 items-center justify-center font-mono text-[0.5rem] text-text-dim"
                >
                  {letter}
                </span>
              ))}
            </div>

            {/* Zone cells */}
            <div
              className="flex-1"
              style={{
                display: 'grid',
                gridTemplateColumns: `repeat(${GRID_COLS}, 1fr)`,
                gridTemplateRows: `repeat(${GRID_ROWS}, 1fr)`,
                gap: '4px',
              }}
            >
              {Array.from({ length: GRID_ROWS }, (_, row) =>
                Array.from({ length: GRID_COLS }, (_, col) => {
                  const zone = lookup[`${col}_${row}`] ?? null;
                  const hasDrone =
                    droneState?.x === col && droneState?.y === row;
                  return (
                    <ZoneCell
                      key={`${col}-${row}`}
                      col={col}
                      row={row}
                      zone={zone}
                      hasDrone={hasDrone}
                    />
                  );
                }),
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="shrink-0 border-t border-border-subtle">
        <MapLegend />
      </div>
    </div>
  );
}
