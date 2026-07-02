/**
 * MainWorkspace — left content area containing the tactical map and activity feed.
 *
 * Layout (top to bottom):
 *   - TacticalMap  (flex-1, fills remaining space)
 *   - ActivityFeed (compact, fixed height)
 */

import { useMissionStore } from '@/stores/missionStore';
import { TacticalMap } from '@/components/dashboard/TacticalMap';
import { ActivityFeed } from '@/components/dashboard/ActivityFeed';

export function MainWorkspace() {
  const missionState = useMissionStore((s) => s.missionState);
  const wsStatus     = useMissionStore((s) => s.wsStatus);

  const isStale = wsStatus !== 'connected' && missionState !== null;

  return (
    <main
      data-testid="main-workspace"
      className="flex min-w-0 flex-1 flex-col gap-2 overflow-hidden p-2"
    >
      {/* Tactical map — takes the majority of the space */}
      <div className="min-h-0 flex-1">
        <TacticalMap
          zoneStates={missionState?.zone_states ?? {}}
          droneState={missionState?.drone_state ?? null}
          exploredPercentage={missionState?.explored_percentage ?? 0}
          isStale={isStale}
        />
      </div>

      {/* Activity feed — compact strip at the bottom */}
      <div className="h-36 shrink-0">
        <ActivityFeed
          alerts={missionState?.active_alerts ?? []}
          wsStatus={wsStatus}
        />
      </div>
    </main>
  );
}
