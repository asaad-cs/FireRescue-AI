/**
 * ReplayControls — replaces MissionControls in the nav bar during replay.
 *
 * Shows: REPLAY label, frame counter (X/N), amber progress bar,
 * speed selector (0.5×/1×/2×), PAUSE/RESUME, RESTART, EXIT.
 *
 * Reads and drives the Zustand replay slice directly — no props needed.
 * Returns null when not in replay mode.
 */

import { useMissionStore } from '@/stores/missionStore';
import type { ReplaySpeed } from '@/stores/missionStore';

const SPEED_OPTIONS: ReplaySpeed[] = [0.5, 1, 2];
const SPEED_LABEL: Record<ReplaySpeed, string> = { 0.5: '0.5×', 1: '1×', 2: '2×' };

export function ReplayControls() {
  const isReplaying    = useMissionStore((s) => s.isReplaying);
  const replayPaused   = useMissionStore((s) => s.replayPaused);
  const replayIndex    = useMissionStore((s) => s.replayIndex);
  const replaySpeed    = useMissionStore((s) => s.replaySpeed);
  const replayHistory  = useMissionStore((s) => s.replayHistory);
  const pauseReplay    = useMissionStore((s) => s.pauseReplay);
  const resumeReplay   = useMissionStore((s) => s.resumeReplay);
  const restartReplay  = useMissionStore((s) => s.restartReplay);
  const exitReplay     = useMissionStore((s) => s.exitReplay);
  const setReplaySpeed = useMissionStore((s) => s.setReplaySpeed);

  if (!isReplaying) return null;

  const total = replayHistory.length;
  const current = replayIndex + 1;
  const progressPct = total > 1 ? (replayIndex / (total - 1)) * 100 : 0;
  const atEnd = replayIndex >= total - 1;

  return (
    <div
      data-testid="replay-controls"
      className="flex items-center gap-3"
      role="region"
      aria-label="Replay controls"
    >
      {/* Label */}
      <span
        className="font-mono text-xs font-bold tracking-widest"
        style={{ color: '#f59e0b' }}
      >
        REPLAY
      </span>

      {/* Frame counter */}
      <span
        data-testid="replay-frame-counter"
        className="font-mono text-xs tabular-nums text-text-secondary"
        aria-label={`Frame ${current} of ${total}`}
      >
        {current}/{total}
      </span>

      {/* Progress bar */}
      <div
        className="h-1 w-24 overflow-hidden rounded-full bg-bg-surface"
        aria-hidden="true"
      >
        <div
          data-testid="replay-progress-bar"
          className="h-full rounded-full transition-all"
          style={{ width: `${progressPct}%`, backgroundColor: '#f59e0b' }}
        />
      </div>

      {/* Speed buttons */}
      <div className="flex items-center gap-0.5" aria-label="Replay speed">
        {SPEED_OPTIONS.map((s) => (
          <button
            key={s}
            data-testid={`replay-speed-${s}`}
            onClick={() => setReplaySpeed(s)}
            className="rounded px-1.5 py-0.5 font-mono text-2xs font-semibold focus:outline-none focus:ring-1"
            style={{
              color: replaySpeed === s ? '#f59e0b' : '#64748b',
              border: `1px solid ${replaySpeed === s ? '#f59e0b' : '#334155'}`,
              backgroundColor: replaySpeed === s ? '#f59e0b15' : 'transparent',
            }}
            aria-pressed={replaySpeed === s}
            aria-label={`Set replay speed to ${SPEED_LABEL[s]}`}
          >
            {SPEED_LABEL[s]}
          </button>
        ))}
      </div>

      {/* Separator */}
      <span className="text-border-strong" aria-hidden="true">|</span>

      {/* PAUSE / RESUME — hidden when at the last frame */}
      {!atEnd && (
        replayPaused ? (
          <button
            data-testid="btn-replay-resume"
            onClick={resumeReplay}
            className="rounded border border-status-active px-2.5 py-1 font-mono text-2xs font-semibold text-status-active hover:bg-status-active/10 focus:outline-none focus:ring-1 focus:ring-status-active"
            aria-label="Resume replay"
          >
            RESUME
          </button>
        ) : (
          <button
            data-testid="btn-replay-pause"
            onClick={pauseReplay}
            className="rounded border border-status-paused px-2.5 py-1 font-mono text-2xs font-semibold text-status-paused hover:bg-status-paused/10 focus:outline-none focus:ring-1 focus:ring-status-paused"
            aria-label="Pause replay"
          >
            PAUSE
          </button>
        )
      )}

      {/* RESTART */}
      <button
        data-testid="btn-replay-restart"
        onClick={restartReplay}
        className="rounded border border-border-strong px-2.5 py-1 font-mono text-2xs font-semibold text-text-secondary hover:bg-bg-surface focus:outline-none focus:ring-1 focus:ring-border-strong"
        aria-label="Restart replay"
      >
        RESTART
      </button>

      {/* EXIT */}
      <button
        data-testid="btn-replay-exit"
        onClick={exitReplay}
        className="rounded border border-alert-critical-border px-2.5 py-1 font-mono text-2xs font-semibold text-alert-critical-text hover:bg-alert-critical-bg focus:outline-none focus:ring-1 focus:ring-alert-critical-border"
        aria-label="Exit replay"
      >
        EXIT
      </button>
    </div>
  );
}
