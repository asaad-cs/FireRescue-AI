/**
 * MissionControls — mission status, timer, and action buttons.
 *
 * Shows context-appropriate buttons:
 *   IDLE      → [START]
 *   ACTIVE    → [PAUSE] [END]
 *   PAUSED    → [RESUME] [END]
 *   ENDED     → (no actions)
 *
 * Callbacks handle API calls; this component is pure UI.
 */

import { MissionStatus } from '@/types/mission';
import { formatElapsed, formatMissionId } from '@/utils/format';

// ── Status dot ────────────────────────────────────────────────────────────────

const STATUS_DOT_COLOR: Record<MissionStatus, string> = {
  [MissionStatus.IDLE]:             '#64748b',
  [MissionStatus.INITIALIZING]:     '#60a5fa',
  [MissionStatus.ACTIVE]:           '#22c55e',
  [MissionStatus.PAUSED]:           '#f59e0b',
  [MissionStatus.ENDED]:            '#475569',
  [MissionStatus.CONNECTION_LOST]:  '#ef4444',
  [MissionStatus.ERROR]:            '#ef4444',
};

const STATUS_LABEL: Record<MissionStatus, string> = {
  [MissionStatus.IDLE]:             'IDLE',
  [MissionStatus.INITIALIZING]:     'INITIALIZING',
  [MissionStatus.ACTIVE]:           'MISSION ACTIVE',
  [MissionStatus.PAUSED]:           'PAUSED',
  [MissionStatus.ENDED]:            'MISSION ENDED',
  [MissionStatus.CONNECTION_LOST]:  'CONNECTION LOST',
  [MissionStatus.ERROR]:            'SYSTEM ERROR',
};

// ── Props ─────────────────────────────────────────────────────────────────────

interface MissionControlsProps {
  status: MissionStatus;
  missionId: string;
  elapsedSeconds: number;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onEnd: () => void;
  isLoading?: boolean;
  error?: string | null;
  /** Whether replay data is available (history recorded from completed mission). */
  canReplay?: boolean;
  /** Called when the user clicks the REPLAY button. */
  onReplay?: () => void;
}

// ── Root component ────────────────────────────────────────────────────────────

export function MissionControls({
  status,
  missionId,
  elapsedSeconds,
  onStart,
  onPause,
  onResume,
  onEnd,
  isLoading = false,
  error = null,
  canReplay = false,
  onReplay,
}: MissionControlsProps) {
  const dotColor = STATUS_DOT_COLOR[status];
  const label = STATUS_LABEL[status];
  const showTimer = status !== MissionStatus.IDLE;

  return (
    <div
      data-testid="mission-controls"
      className="flex items-center gap-3"
      role="region"
      aria-label="Mission controls"
    >
      {/* Status indicator */}
      <div className="flex items-center gap-2">
        <span
          aria-hidden="true"
          className="h-2 w-2 rounded-full"
          style={{
            backgroundColor: dotColor,
            boxShadow:
              status === MissionStatus.ACTIVE
                ? `0 0 6px ${dotColor}`
                : undefined,
          }}
        />
        <span className="font-mono text-xs font-semibold text-text-primary">
          {label}
        </span>
      </div>

      {/* Mission ID */}
      {missionId && (
        <span className="font-mono text-2xs text-text-muted" title={missionId}>
          {formatMissionId(missionId)}
        </span>
      )}

      {/* Timer */}
      {showTimer && (
        <span
          data-testid="mission-timer"
          className="font-mono text-xs tabular-nums text-text-secondary"
          aria-label={`Elapsed time: ${formatElapsed(elapsedSeconds)}`}
        >
          {formatElapsed(elapsedSeconds)}
        </span>
      )}

      {/* Separator */}
      {(status === MissionStatus.IDLE ||
        status === MissionStatus.ACTIVE ||
        status === MissionStatus.PAUSED ||
        status === MissionStatus.ENDED) && (
        <span className="text-border-strong">|</span>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-1.5">
        {status === MissionStatus.IDLE && (
          <button
            data-testid="btn-start"
            onClick={onStart}
            disabled={isLoading}
            className="rounded border border-status-active px-2.5 py-1 font-mono text-2xs font-semibold text-status-active hover:bg-status-active/10 focus:outline-none focus:ring-1 focus:ring-status-active disabled:opacity-50"
            aria-label="Start mission"
          >
            START
          </button>
        )}

        {status === MissionStatus.ACTIVE && (
          <>
            <button
              data-testid="btn-pause"
              onClick={onPause}
              disabled={isLoading}
              className="rounded border border-status-paused px-2.5 py-1 font-mono text-2xs font-semibold text-status-paused hover:bg-status-paused/10 focus:outline-none focus:ring-1 focus:ring-status-paused disabled:opacity-50"
              aria-label="Pause mission"
            >
              PAUSE
            </button>
            <button
              data-testid="btn-end"
              onClick={onEnd}
              disabled={isLoading}
              className="rounded border border-alert-critical-border px-2.5 py-1 font-mono text-2xs font-semibold text-alert-critical-text hover:bg-alert-critical-bg focus:outline-none focus:ring-1 focus:ring-alert-critical-border disabled:opacity-50"
              aria-label="End mission"
            >
              END
            </button>
          </>
        )}

        {status === MissionStatus.PAUSED && (
          <>
            <button
              data-testid="btn-resume"
              onClick={onResume}
              disabled={isLoading}
              className="rounded border border-status-active px-2.5 py-1 font-mono text-2xs font-semibold text-status-active hover:bg-status-active/10 focus:outline-none focus:ring-1 focus:ring-status-active disabled:opacity-50"
              aria-label="Resume mission"
            >
              RESUME
            </button>
            <button
              data-testid="btn-end"
              onClick={onEnd}
              disabled={isLoading}
              className="rounded border border-alert-critical-border px-2.5 py-1 font-mono text-2xs font-semibold text-alert-critical-text hover:bg-alert-critical-bg focus:outline-none focus:ring-1 focus:ring-alert-critical-border disabled:opacity-50"
              aria-label="End mission"
            >
              END
            </button>
          </>
        )}

        {status === MissionStatus.ENDED && (
          <>
            <button
              data-testid="btn-new-mission"
              onClick={onStart}
              disabled={isLoading}
              className="rounded border border-status-active px-2.5 py-1 font-mono text-2xs font-semibold text-status-active hover:bg-status-active/10 focus:outline-none focus:ring-1 focus:ring-status-active disabled:opacity-50"
              aria-label="Start new mission"
            >
              NEW MISSION
            </button>
            {canReplay && onReplay && (
              <button
                data-testid="btn-replay"
                onClick={onReplay}
                disabled={isLoading}
                className="rounded border px-2.5 py-1 font-mono text-2xs font-semibold focus:outline-none focus:ring-1 disabled:opacity-50"
                style={{
                  color: '#f59e0b',
                  borderColor: '#f59e0b',
                }}
                aria-label="Replay mission"
              >
                REPLAY
              </button>
            )}
          </>
        )}
      </div>

      {/* Inline error */}
      {error && (
        <span className="font-mono text-2xs text-alert-critical-text" role="alert">
          {error}
        </span>
      )}

      {/* Loading indicator */}
      {isLoading && (
        <span className="font-mono text-2xs text-text-muted" aria-live="polite">
          …
        </span>
      )}
    </div>
  );
}
