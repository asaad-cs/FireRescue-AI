/**
 * TopNavigation — application header with live mission controls.
 *
 * Left:   App branding
 * Centre: MissionControls (status dot, timer, action buttons)
 * Right:  Connection indicator
 *
 * API calls (pause/resume/end) are handled here; MissionControls is pure UI.
 */

import { useState, useCallback } from 'react';
import { useMissionStore } from '@/stores/missionStore';
import { MissionControls } from '@/components/dashboard/MissionControls';
import { ReplayControls } from '@/components/dashboard/ReplayControls';
import { ConnectionIndicator } from '@/components/placeholders/ConnectionIndicator';
import { MissionStatus } from '@/types/mission';
import { startMission, pauseMission, resumeMission, endMission } from '@/services/api';

export function TopNavigation() {
  const wsStatus          = useMissionStore((s) => s.wsStatus);
  const reconnectAttempts = useMissionStore((s) => s.reconnectAttempts);
  const missionState      = useMissionStore((s) => s.missionState);
  const isReplaying       = useMissionStore((s) => s.isReplaying);
  const replayHistory     = useMissionStore((s) => s.replayHistory);
  const startReplay       = useMissionStore((s) => s.startReplay);

  const status         = missionState?.status ?? MissionStatus.IDLE;
  const missionId      = missionState?.mission_id ?? '';
  const elapsedSeconds = missionState?.elapsed_seconds ?? 0;
  const canReplay      = replayHistory.length > 0 && status === MissionStatus.ENDED;

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError]         = useState<string | null>(null);

  const callApi = useCallback(async (fn: () => Promise<void>) => {
    setIsLoading(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Request failed';
      setError(msg.length > 60 ? msg.substring(0, 60) + '…' : msg);
      // Clear the error after 4 seconds
      setTimeout(() => setError(null), 4000);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <header
      data-testid="top-navigation"
      className="flex h-12 shrink-0 items-center justify-between border-b border-border-default bg-bg-surface px-4"
    >
      {/* Left: app name */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className="h-3 w-3 rounded-sm"
            style={{ backgroundColor: '#ef4444', boxShadow: '0 0 6px #ef4444aa' }}
          />
          <span className="font-mono text-sm font-bold tracking-widest text-text-primary">
            FIRERESCUE AI
          </span>
        </div>
        <span
          className="rounded px-1.5 py-0.5 font-mono text-[0.5rem] font-semibold uppercase tracking-widest"
          style={{ color: '#445566', backgroundColor: '#ffffff08', border: '1px solid #1a2435' }}
        >
          Research Prototype
        </span>
      </div>

      {/* Centre: replay controls during replay, mission controls otherwise */}
      <div className="flex items-center">
        {isReplaying ? (
          <ReplayControls />
        ) : (
          <MissionControls
            status={status}
            missionId={missionId}
            elapsedSeconds={elapsedSeconds}
            onStart={() => callApi(startMission)}
            onPause={() => callApi(pauseMission)}
            onResume={() => callApi(resumeMission)}
            onEnd={() => callApi(endMission)}
            isLoading={isLoading}
            error={error}
            canReplay={canReplay}
            onReplay={startReplay}
          />
        )}
      </div>

      {/* Right: connection status */}
      <div className="flex items-center">
        <ConnectionIndicator
          wsStatus={wsStatus}
          reconnectAttempts={reconnectAttempts}
        />
      </div>
    </header>
  );
}
