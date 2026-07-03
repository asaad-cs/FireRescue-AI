/**
 * MissionTimeline — horizontal scrollable strip of mission events.
 *
 * Events are derived from active_alerts sorted chronologically (oldest left,
 * newest right). Auto-scrolls to the latest event when the user is already
 * at the right end of the timeline.
 *
 * Each event is a compact chip coloured by alert level.
 */

import { useRef, useEffect, useState } from 'react';
import { AlertLevel, MissionStatus, type Alert } from '@/types/mission';
import { formatTimestamp } from '@/utils/format';

// ── Chip styles ───────────────────────────────────────────────────────────────

const CHIP_STYLE: Record<AlertLevel, { bg: string; border: string; text: string }> = {
  [AlertLevel.INFO]: {
    bg: '#071828', border: '#1e4d7a', text: '#60a5fa',
  },
  [AlertLevel.WARNING]: {
    bg: '#1e1200', border: '#7a4d00', text: '#fbbf24',
  },
  [AlertLevel.CRITICAL]: {
    bg: '#200808', border: '#7a1818', text: '#f87171',
  },
  [AlertLevel.EMERGENCY]: {
    bg: '#2a0000', border: '#cc0000', text: '#ffffff',
  },
};

// ── Level abbreviation ────────────────────────────────────────────────────────

const LEVEL_ABBR: Record<AlertLevel, string> = {
  [AlertLevel.INFO]:      'INF',
  [AlertLevel.WARNING]:   'WRN',
  [AlertLevel.CRITICAL]:  'CRT',
  [AlertLevel.EMERGENCY]: 'EMG',
};

// ── Props ─────────────────────────────────────────────────────────────────────

interface MissionTimelineProps {
  alerts: Alert[];
  status: MissionStatus;
}

// ── Root component ────────────────────────────────────────────────────────────

export function MissionTimeline({ alerts, status }: MissionTimelineProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isAtEnd, setIsAtEnd] = useState(true);

  // Sort oldest → newest for left-to-right display
  const sorted = [...alerts].sort(
    (a, b) =>
      new Date(a.triggered_at).getTime() - new Date(b.triggered_at).getTime(),
  );

  // Auto-scroll to end when new events arrive, only if already at end
  useEffect(() => {
    if (!isAtEnd || !scrollRef.current) return;
    scrollRef.current.scrollLeft = scrollRef.current.scrollWidth;
  }, [sorted.length, isAtEnd]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 10;
    setIsAtEnd(atEnd);
  };

  return (
    <div
      data-testid="mission-timeline"
      className="flex h-full items-center gap-0 overflow-hidden"
      aria-label="Mission timeline"
    >
      {/* Label — the left block doubles as the anchor for future
          replay/scrubbing controls; the strip itself stays a clean rail. */}
      <div className="flex shrink-0 flex-col items-center justify-center border-r border-border-subtle px-3">
        <span className="font-mono text-2xs font-semibold tracking-widest text-text-muted">
          TIMELINE
        </span>
        <span className="mt-0.5 font-mono text-[0.55rem] text-text-dim">{status}</span>
      </div>

      {/* Scrollable event chips */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex flex-1 items-center gap-2 overflow-x-auto px-3 py-2"
        style={{ scrollbarWidth: 'thin' }}
      >
        {sorted.length === 0 ? (
          <span className="shrink-0 font-mono text-2xs text-text-dim">
            No events recorded
          </span>
        ) : (
          sorted.map((alert) => {
            const style = CHIP_STYLE[alert.level];
            return (
              <div
                key={alert.alert_id}
                data-testid={`timeline-event-${alert.alert_id}`}
                role="listitem"
                aria-label={`${alert.level} at ${formatTimestamp(alert.triggered_at)}: ${alert.message}`}
                style={{
                  backgroundColor: style.bg,
                  borderColor: style.border,
                  color: style.text,
                  boxShadow: `inset 0 -2px 0 ${style.border}`,
                }}
                className="flex shrink-0 items-center gap-1.5 rounded-md border px-2.5 py-1 transition-transform hover:-translate-y-px"
              >
                <span className="font-mono text-[0.6rem] font-bold opacity-90">
                  {LEVEL_ABBR[alert.level]}
                </span>
                <span className="font-mono text-[0.6rem] text-text-muted">
                  {formatTimestamp(alert.triggered_at)}
                </span>
                <span
                  className="max-w-[14rem] truncate font-mono text-[0.6rem]"
                  title={alert.message}
                >
                  {alert.message}
                </span>
              </div>
            );
          })
        )}
      </div>

      {/* Scroll hint when not at end */}
      {!isAtEnd && (
        <div className="pointer-events-none absolute right-0 h-full w-8 bg-gradient-to-l from-bg-surface to-transparent" />
      )}
    </div>
  );
}
