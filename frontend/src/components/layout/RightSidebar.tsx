/**
 * RightSidebar — operational panels stacked vertically (Phase 8I.1).
 *
 * Top to bottom:
 *   MissionStatistics (compact summary row)
 *   MissionOpsPanel   (mission + AI operations summary)
 *   AlertPanel        (flex-[3] — highest priority, most space)
 *   DroneStatus       (flex-[2])
 *   VictimSignals     (flex-[2])
 */

import { useMissionStore } from '@/stores/missionStore';
import { AlertPanel }        from '@/components/dashboard/AlertPanel';
import { DroneStatus }       from '@/components/dashboard/DroneStatus';
import { VictimSignals }     from '@/components/dashboard/VictimSignals';
import { MissionStatistics } from '@/components/dashboard/MissionStatistics';
import { MissionOpsPanel }   from '@/components/dashboard/MissionOpsPanel';
import { MissionStatus } from '@/types/mission';

export function RightSidebar() {
  const missionState          = useMissionStore((s) => s.missionState);
  const wsStatus              = useMissionStore((s) => s.wsStatus);
  const acknowledgedAlertIds  = useMissionStore((s) => s.acknowledgedAlertIds);
  const acknowledgeAlert      = useMissionStore((s) => s.acknowledgeAlert);

  const isStale = wsStatus !== 'connected' && missionState !== null;

  const alerts           = missionState?.active_alerts ?? [];
  const alertCount       = missionState?.alert_count ?? 0;
  const droneState       = missionState?.drone_state ?? null;
  const latestReadings   = missionState?.latest_readings ?? {
    temperature:   null,
    co_level:      null,
    smoke_density: null,
  };
  const zoneStates         = missionState?.zone_states ?? {};
  const victimSignalCount  = missionState?.victim_signal_count ?? 0;

  const isDroneStale =
    isStale ||
    missionState?.status === MissionStatus.PAUSED ||
    missionState?.status === MissionStatus.CONNECTION_LOST;

  return (
    <aside
      data-testid="right-sidebar"
      className="flex w-96 shrink-0 flex-col gap-2 overflow-y-auto border-l border-border-default bg-bg-base p-2"
    >
      {/* Mission stats — compact summary row at top */}
      <MissionStatistics missionState={missionState} />

      {/* Operations summary — mission + AI status (Phase 8I.1) */}
      <div className="shrink-0">
        <MissionOpsPanel missionState={missionState} />
      </div>

      {/* Alert panel — most vertical space, highest priority */}
      <div className="min-h-[10rem] flex-[3] overflow-hidden">
        <AlertPanel
          alerts={alerts}
          alertCount={alertCount}
          acknowledgedAlertIds={acknowledgedAlertIds}
          onAcknowledge={acknowledgeAlert}
        />
      </div>

      {/* Drone status */}
      <div className="min-h-[8rem] flex-[2] overflow-hidden">
        <DroneStatus
          droneState={droneState}
          latestReadings={latestReadings}
          zoneStates={zoneStates}
          isStale={isDroneStale}
        />
      </div>

      {/* Victim signals */}
      <div className="min-h-[6rem] flex-[2] overflow-hidden">
        <VictimSignals
          zoneStates={zoneStates}
          victimSignalCount={victimSignalCount}
        />
      </div>
    </aside>
  );
}
