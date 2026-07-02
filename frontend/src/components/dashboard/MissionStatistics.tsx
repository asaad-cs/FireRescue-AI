/**
 * MissionStatistics — compact four-number summary of the current mission.
 *
 * Shows: explored %, elapsed time, active alerts, victim signal count.
 * All values come directly from MissionState — no derived computation here.
 */

import { MissionStatus, type MissionState } from '@/types/mission';
import { formatElapsed, formatPct } from '@/utils/format';

// ── Stat cell ─────────────────────────────────────────────────────────────────

interface StatCellProps {
  label: string;
  value: string;
  accent?: string;
  dim?: boolean;
}

function StatCell({ label, value, accent, dim }: StatCellProps) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span
        className="font-mono text-sm font-bold tabular-nums leading-none"
        style={{ color: accent ?? '#dde6f0', opacity: dim ? 0.4 : 1 }}
      >
        {value}
      </span>
      <span className="font-mono text-[0.55rem] uppercase tracking-wider text-text-muted">
        {label}
      </span>
    </div>
  );
}

// ── Root component ────────────────────────────────────────────────────────────

interface MissionStatisticsProps {
  missionState: MissionState | null;
}

export function MissionStatistics({ missionState }: MissionStatisticsProps) {
  const explored    = missionState ? formatPct(missionState.explored_percentage) : '—';
  const elapsed     = missionState ? formatElapsed(missionState.elapsed_seconds) : '—';
  const alertCount = missionState ? String(missionState.alert_count) : '—';
  const signalCount = missionState ? String(missionState.victim_signal_count) : '—';

  const alertAccent  = missionState && missionState.alert_count  > 0 ? '#f87171' : undefined;
  const signalAccent = missionState && missionState.victim_signal_count > 0 ? '#f59e0b' : undefined;
  const noData       = !missionState;

  return (
    <div
      data-testid="mission-statistics"
      className="shrink-0 rounded border border-border-default bg-bg-surface px-3 py-2.5"
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-2xs font-semibold uppercase tracking-wider text-text-muted">
          Mission Statistics
        </span>
        {missionState && (
          <span
            className="rounded px-1.5 py-0.5 font-mono text-[0.5rem] font-bold tracking-widest"
            style={{
              color:
                missionState.status === MissionStatus.ACTIVE ? '#22c55e' :
                missionState.status === MissionStatus.PAUSED ? '#f59e0b' :
                missionState.status === MissionStatus.ENDED  ? '#475569' :
                '#64748b',
              backgroundColor:
                missionState.status === MissionStatus.ACTIVE ? '#22c55e15' :
                missionState.status === MissionStatus.PAUSED ? '#f59e0b15' :
                '#ffffff08',
              border: '1px solid currentColor',
            }}
          >
            {missionState.status}
          </span>
        )}
      </div>

      <div className="grid grid-cols-4 divide-x divide-border-subtle">
        <StatCell label="Explored"    value={explored}    dim={noData} />
        <StatCell label="Elapsed"     value={elapsed}     dim={noData} />
        <StatCell label="Alerts"      value={alertCount}  accent={alertAccent}  dim={noData} />
        <StatCell label="Signals"     value={signalCount} accent={signalAccent} dim={noData} />
      </div>
    </div>
  );
}
