/**
 * DetectionCards — modern per-class AI detection cards (Phase 8I.1).
 *
 * One card per detection class (🔥 Fire, 🌫 Smoke, 👤 Victim), fed by
 * the current vision frame:
 *   - status (DETECTED / CLEAR / NO FEED)
 *   - detection count in the current frame
 *   - highest confidence
 *   - class color indicator
 */

import { type VisionFrame } from '@/types/mission';

interface CardSpec {
  key: string;          // detection class_name in VisionFrame
  icon: string;
  title: string;
  color: string;
}

const CARDS: CardSpec[] = [
  { key: 'fire',   icon: '🔥', title: 'Fire',   color: '#ef4444' },
  { key: 'smoke',  icon: '🌫', title: 'Smoke',  color: '#f97316' },
  { key: 'person', icon: '👤', title: 'Victim', color: '#3b82f6' },
];

interface DetectionCardsProps {
  vision: VisionFrame | null;
}

function Card({ spec, vision }: { spec: CardSpec; vision: VisionFrame | null }) {
  const detections =
    vision?.detections.filter((d) => d.class_name === spec.key) ?? [];
  const detected = detections.length > 0;
  const best = detected
    ? Math.max(...detections.map((d) => d.confidence))
    : null;
  const status = !vision ? 'NO FEED' : detected ? 'DETECTED' : 'CLEAR';
  const statusColor = !vision ? '#445566' : detected ? spec.color : '#22c55e';

  return (
    <div
      data-testid={`detection-card-${spec.key}`}
      className="flex min-w-0 flex-1 flex-col justify-between rounded-lg border bg-bg-surface p-2.5"
      style={{
        borderColor: detected ? spec.color : '#1a2435',
        boxShadow: detected ? `inset 3px 0 0 ${spec.color}` : 'inset 3px 0 0 #1a2435',
      }}
    >
      <div className="flex items-center justify-between gap-1">
        <span className="flex items-center gap-1.5 font-mono text-2xs font-semibold text-text-primary">
          <span aria-hidden="true">{spec.icon}</span> {spec.title}
        </span>
        <span
          aria-hidden="true"
          className="h-2 w-2 shrink-0 rounded-full"
          style={{
            backgroundColor: statusColor,
            boxShadow: detected ? `0 0 6px ${statusColor}` : undefined,
          }}
        />
      </div>
      <div className="mt-1 flex items-end justify-between gap-1">
        <span
          data-testid={`detection-status-${spec.key}`}
          className="font-mono text-[0.55rem] font-bold tracking-widest"
          style={{ color: statusColor }}
        >
          {status}
          {detected && detections.length > 1 ? ` ×${detections.length}` : ''}
        </span>
        <span className="font-mono text-sm font-bold" style={{ color: detected ? spec.color : '#2d3d50' }}>
          {best !== null ? `${Math.round(best * 100)}%` : '—'}
        </span>
      </div>
    </div>
  );
}

export function DetectionCards({ vision }: DetectionCardsProps) {
  return (
    <div data-testid="detection-cards" className="flex h-full gap-2">
      {CARDS.map((spec) => (
        <Card key={spec.key} spec={spec} vision={vision} />
      ))}
    </div>
  );
}
