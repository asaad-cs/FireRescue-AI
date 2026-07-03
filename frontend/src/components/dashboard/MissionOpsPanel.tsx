/**
 * MissionOpsPanel — operations summary for the command center (Phase 8I.1).
 *
 * Everything is derived from the MissionState the backend already
 * pushes; no new data contracts:
 *   mission status · timer · rooms scanned/remaining · victims ·
 *   hazards · detector · model · inference time · camera source
 */

import { HazardLevel, MissionStatus, type MissionState } from '@/types/mission';
import { formatElapsed } from '@/utils/format';

const STATUS_COLOR: Record<MissionStatus, string> = {
  [MissionStatus.IDLE]:            '#445566',
  [MissionStatus.INITIALIZING]:    '#60a5fa',
  [MissionStatus.ACTIVE]:          '#22c55e',
  [MissionStatus.PAUSED]:          '#f59e0b',
  [MissionStatus.ENDED]:           '#8097b0',
  [MissionStatus.CONNECTION_LOST]: '#ef4444',
  [MissionStatus.ERROR]:           '#ef4444',
};

const HAZARDOUS = new Set<HazardLevel>([
  HazardLevel.MODERATE,
  HazardLevel.HIGH,
  HazardLevel.CRITICAL,
]);

interface MissionOpsPanelProps {
  missionState: MissionState | null;
}

function Row({ label, value, valueColor }: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-2 py-0.5">
      <span className="font-mono text-2xs text-text-muted">{label}</span>
      <span
        className="truncate font-mono text-2xs font-semibold text-text-primary"
        style={valueColor ? { color: valueColor } : undefined}
        title={value}
      >
        {value}
      </span>
    </div>
  );
}

export function MissionOpsPanel({ missionState }: MissionOpsPanelProps) {
  const status = missionState?.status ?? MissionStatus.IDLE;
  const scanned = Object.keys(missionState?.zone_states ?? {}).length;
  const explored = missionState?.explored_percentage ?? 0;
  // Total zone count is not part of MissionState; derive it from the
  // pre-computed percentage the backend already sends.
  const total = explored > 0 ? Math.round((scanned * 100) / explored) : null;
  const remaining = total !== null ? Math.max(total - scanned, 0) : null;
  const hazards = Object.values(missionState?.zone_states ?? {}).filter((z) =>
    HAZARDOUS.has(z.hazard_level)
  ).length;
  const vision = missionState?.vision ?? null;

  return (
    <div
      data-testid="mission-ops-panel"
      className="flex flex-col rounded-lg border border-border-default bg-bg-surface"
    >
      <div className="flex shrink-0 items-center justify-between border-b border-border-subtle px-3 py-2">
        <span className="font-mono text-xs font-semibold tracking-wider text-text-primary">
          OPERATIONS
        </span>
        <span
          className="rounded px-2 py-0.5 font-mono text-[0.55rem] font-bold tracking-widest"
          style={{
            color: STATUS_COLOR[status],
            backgroundColor: `${STATUS_COLOR[status]}1a`,
            border: `1px solid ${STATUS_COLOR[status]}55`,
          }}
        >
          {status}
        </span>
      </div>

      <div className="flex flex-col px-3 py-1.5">
        <Row label="Mission timer" value={formatElapsed(missionState?.elapsed_seconds ?? 0)} />
        <Row label="Rooms scanned" value={String(scanned)} />
        <Row
          label="Rooms remaining"
          value={remaining !== null ? String(remaining) : '—'}
        />
        <Row
          label="Victims detected"
          value={String(missionState?.victim_signal_count ?? 0)}
          valueColor={(missionState?.victim_signal_count ?? 0) > 0 ? '#f87171' : undefined}
        />
        <Row
          label="Hazards detected"
          value={String(hazards)}
          valueColor={hazards > 0 ? '#f97316' : undefined}
        />
        <div className="my-1 border-t border-border-subtle" />
        <Row label="Detector" value={(vision?.detector_name ?? 'ground truth').toUpperCase()} />
        <Row label="Model" value={vision?.model_name || '—'} />
        <Row
          label="Inference time"
          value={vision ? `${vision.inference_ms.toFixed(1)} ms` : '—'}
        />
        <Row label="Camera source" value={vision ? 'SIM-CAM-01' : 'no feed'} />
      </div>
    </div>
  );
}
