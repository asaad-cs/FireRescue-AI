import { useEffect, useRef } from 'react';
import { useMissionStore } from '@/stores/missionStore';
import type { ReplaySpeed } from '@/stores/missionStore';

const INTERVAL_MS: Record<ReplaySpeed, number> = {
  0.5: 2000,
  1: 1000,
  2: 500,
};

/**
 * Drives replay playback — mounts a setInterval that calls stepReplay()
 * at the appropriate speed. The interval is torn down whenever replay
 * is paused, stopped, or the speed changes.
 *
 * Mount this once in AppLayout so it runs for the application lifetime.
 */
export function useReplayEngine(): void {
  const isReplaying  = useMissionStore((s) => s.isReplaying);
  const replayPaused = useMissionStore((s) => s.replayPaused);
  const replaySpeed  = useMissionStore((s) => s.replaySpeed);
  const stepReplay   = useMissionStore((s) => s.stepReplay);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (!isReplaying || replayPaused) return;

    const ms = INTERVAL_MS[replaySpeed] ?? 1000;
    intervalRef.current = setInterval(stepReplay, ms);

    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isReplaying, replayPaused, replaySpeed, stepReplay]);
}
