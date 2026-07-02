/**
 * BottomTimeline — footer strip containing the chronological event timeline.
 */

import { useMissionStore } from '@/stores/missionStore';
import { MissionTimeline } from '@/components/dashboard/MissionTimeline';
import { MissionStatus } from '@/types/mission';

export function BottomTimeline() {
  const missionState = useMissionStore((s) => s.missionState);

  return (
    <footer
      data-testid="bottom-timeline"
      className="relative h-24 shrink-0 border-t border-border-default bg-bg-surface"
    >
      <MissionTimeline
        alerts={missionState?.active_alerts ?? []}
        status={missionState?.status ?? MissionStatus.IDLE}
      />
    </footer>
  );
}
