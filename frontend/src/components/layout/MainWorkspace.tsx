/**
 * MainWorkspace — the command center's primary content area (Phase 8I.1).
 *
 * Two columns:
 *   Left  (camera column) — MissionCamera (the primary visual element,
 *          sized for future video playback) over the DetectionCards row
 *   Right (situation column) — TacticalMap over the ActivityFeed
 */

import { useMissionStore } from '@/stores/missionStore';
import { TacticalMap } from '@/components/dashboard/TacticalMap';
import { MissionCamera } from '@/components/dashboard/MissionCamera';
import { DetectionCards } from '@/components/dashboard/DetectionCards';
import { ActivityFeed } from '@/components/dashboard/ActivityFeed';

export function MainWorkspace() {
  const missionState = useMissionStore((s) => s.missionState);
  const wsStatus     = useMissionStore((s) => s.wsStatus);
  const isReplaying  = useMissionStore((s) => s.isReplaying);

  const isStale = wsStatus !== 'connected' && missionState !== null;
  const vision = missionState?.vision ?? null;

  return (
    <main
      data-testid="main-workspace"
      className="flex min-w-0 flex-1 gap-2 overflow-hidden p-2"
    >
      {/* Camera column — the primary visual element */}
      <div className="flex min-w-0 flex-[5] flex-col gap-2">
        <div className="min-h-0 flex-1">
          <MissionCamera
            vision={vision}
            missionId={missionState?.mission_id ?? null}
            wsStatus={wsStatus}
            isStale={isStale}
            isReplaying={isReplaying}
          />
        </div>
        <div className="h-[4.5rem] shrink-0">
          <DetectionCards vision={vision} />
        </div>
      </div>

      {/* Situation column — building map + activity feed */}
      <div className="flex min-w-0 flex-[4] flex-col gap-2">
        <div className="min-h-0 flex-1">
          <TacticalMap
            zoneStates={missionState?.zone_states ?? {}}
            droneState={missionState?.drone_state ?? null}
            exploredPercentage={missionState?.explored_percentage ?? 0}
            isStale={isStale}
          />
        </div>
        <div className="h-32 shrink-0">
          <ActivityFeed
            alerts={missionState?.active_alerts ?? []}
            wsStatus={wsStatus}
          />
        </div>
      </div>
    </main>
  );
}
