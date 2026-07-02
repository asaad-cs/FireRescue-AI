import { describe, it, expect, beforeEach } from 'vitest';
import { useMissionStore } from '@/stores/missionStore';
import {
  MissionStatus,
  ConnectionStatus,
  type MissionState,
} from '@/types/mission';
import type { ReplaySpeed } from '@/stores/missionStore';

// ─── Minimal valid MissionState ───────────────────────────────────────────────

const MISSION_STATE: MissionState = {
  mission_id: 'test-mission-001',
  status: MissionStatus.ACTIVE,
  started_at: '2026-07-01T10:00:00Z',
  ended_at: null,
  elapsed_seconds: 42,
  drone_state: {
    drone_id: 'drone-1',
    x: 2,
    y: 3,
    floor: 1,
    heading: 0,
    last_seen: '2026-07-01T10:00:42Z',
  },
  zone_states: {},
  active_alerts: [],
  latest_readings: { temperature: 25.5, co_level: 8.0, smoke_density: 0.04 },
  alert_count: 0,
  victim_signal_count: 0,
  explored_percentage: 35,
  connection_status: ConnectionStatus.CONNECTED,
};

// ─── Helper — reset store between tests ──────────────────────────────────────

function resetStore() {
  const store = useMissionStore.getState();
  // Reset replay slice directly so replayHistory is always cleared
  useMissionStore.setState({
    isReplaying: false,
    replayPaused: false,
    replayIndex: 0,
    replaySpeed: 1,
    replayHistory: [],
    finalMissionState: null,
  });
  store.clearMissionState();
  store.setWsStatus('disconnected');
  store.resetReconnectAttempts();
  store.clearAcknowledgedAlerts();
  // Ensure sidebar starts uncollapsed
  if (store.isSidebarCollapsed) store.toggleSidebar();
}

function makeMissionState(overrides: Partial<MissionState> = {}): MissionState {
  return { ...MISSION_STATE, ...overrides };
}

// ─── Connection slice ─────────────────────────────────────────────────────────

describe('missionStore — connection slice', () => {
  beforeEach(resetStore);

  it('initial wsStatus is disconnected', () => {
    expect(useMissionStore.getState().wsStatus).toBe('disconnected');
  });

  it('setWsStatus updates wsStatus', () => {
    useMissionStore.getState().setWsStatus('connected');
    expect(useMissionStore.getState().wsStatus).toBe('connected');
  });

  it('setWsStatus("connected") records lastConnectedAt', () => {
    useMissionStore.getState().setWsStatus('connected');
    expect(useMissionStore.getState().lastConnectedAt).not.toBeNull();
  });

  it('setWsStatus("reconnecting") does not clear lastConnectedAt', () => {
    useMissionStore.getState().setWsStatus('connected');
    const connectedAt = useMissionStore.getState().lastConnectedAt;
    useMissionStore.getState().setWsStatus('reconnecting');
    expect(useMissionStore.getState().lastConnectedAt).toBe(connectedAt);
  });

  it('initial reconnectAttempts is 0', () => {
    expect(useMissionStore.getState().reconnectAttempts).toBe(0);
  });

  it('incrementReconnectAttempts increments by 1', () => {
    useMissionStore.getState().incrementReconnectAttempts();
    useMissionStore.getState().incrementReconnectAttempts();
    expect(useMissionStore.getState().reconnectAttempts).toBe(2);
  });

  it('resetReconnectAttempts resets to 0', () => {
    useMissionStore.getState().incrementReconnectAttempts();
    useMissionStore.getState().incrementReconnectAttempts();
    useMissionStore.getState().resetReconnectAttempts();
    expect(useMissionStore.getState().reconnectAttempts).toBe(0);
  });

  it('setWsStatus("connected") resets reconnectAttempts to 0', () => {
    useMissionStore.getState().incrementReconnectAttempts();
    useMissionStore.getState().setWsStatus('connected');
    expect(useMissionStore.getState().reconnectAttempts).toBe(0);
  });
});

// ─── Mission slice ────────────────────────────────────────────────────────────

describe('missionStore — mission slice', () => {
  beforeEach(resetStore);

  it('initial missionState is null', () => {
    expect(useMissionStore.getState().missionState).toBeNull();
  });

  it('initial lastUpdatedAt is null', () => {
    expect(useMissionStore.getState().lastUpdatedAt).toBeNull();
  });

  it('setMissionState stores the mission state', () => {
    useMissionStore.getState().setMissionState(MISSION_STATE);
    expect(useMissionStore.getState().missionState).toEqual(MISSION_STATE);
  });

  it('setMissionState sets lastUpdatedAt to a non-null ISO string', () => {
    useMissionStore.getState().setMissionState(MISSION_STATE);
    const ts = useMissionStore.getState().lastUpdatedAt;
    expect(ts).not.toBeNull();
    expect(new Date(ts!).toISOString()).toBe(ts);
  });

  it('setMissionState replaces previous state', () => {
    useMissionStore.getState().setMissionState(MISSION_STATE);
    const updated = { ...MISSION_STATE, elapsed_seconds: 100 };
    useMissionStore.getState().setMissionState(updated);
    expect(useMissionStore.getState().missionState?.elapsed_seconds).toBe(100);
  });

  it('clearMissionState resets missionState to null', () => {
    useMissionStore.getState().setMissionState(MISSION_STATE);
    useMissionStore.getState().clearMissionState();
    expect(useMissionStore.getState().missionState).toBeNull();
  });

  it('clearMissionState resets lastUpdatedAt to null', () => {
    useMissionStore.getState().setMissionState(MISSION_STATE);
    useMissionStore.getState().clearMissionState();
    expect(useMissionStore.getState().lastUpdatedAt).toBeNull();
  });

  it('preserves all MissionState fields exactly', () => {
    useMissionStore.getState().setMissionState(MISSION_STATE);
    const stored = useMissionStore.getState().missionState!;
    expect(stored.mission_id).toBe('test-mission-001');
    expect(stored.status).toBe(MissionStatus.ACTIVE);
    expect(stored.elapsed_seconds).toBe(42);
    expect(stored.drone_state?.x).toBe(2);
    expect(stored.latest_readings.temperature).toBe(25.5);
  });
});

// ─── UI slice ─────────────────────────────────────────────────────────────────

describe('missionStore — ui slice', () => {
  beforeEach(resetStore);

  it('initial isSidebarCollapsed is false', () => {
    expect(useMissionStore.getState().isSidebarCollapsed).toBe(false);
  });

  it('toggleSidebar flips isSidebarCollapsed', () => {
    useMissionStore.getState().toggleSidebar();
    expect(useMissionStore.getState().isSidebarCollapsed).toBe(true);
  });

  it('toggleSidebar twice returns to original state', () => {
    useMissionStore.getState().toggleSidebar();
    useMissionStore.getState().toggleSidebar();
    expect(useMissionStore.getState().isSidebarCollapsed).toBe(false);
  });

  it('initial acknowledgedAlertIds is empty', () => {
    expect(useMissionStore.getState().acknowledgedAlertIds).toEqual([]);
  });

  it('acknowledgeAlert adds an alert id', () => {
    useMissionStore.getState().acknowledgeAlert('alert-123');
    expect(useMissionStore.getState().acknowledgedAlertIds).toContain('alert-123');
  });

  it('acknowledgeAlert is idempotent — same id not added twice', () => {
    useMissionStore.getState().acknowledgeAlert('alert-123');
    useMissionStore.getState().acknowledgeAlert('alert-123');
    const ids = useMissionStore.getState().acknowledgedAlertIds;
    expect(ids.filter((id) => id === 'alert-123')).toHaveLength(1);
  });

  it('acknowledgeAlert can track multiple ids', () => {
    useMissionStore.getState().acknowledgeAlert('a1');
    useMissionStore.getState().acknowledgeAlert('a2');
    useMissionStore.getState().acknowledgeAlert('a3');
    expect(useMissionStore.getState().acknowledgedAlertIds).toHaveLength(3);
  });

  it('clearAcknowledgedAlerts resets to empty array', () => {
    useMissionStore.getState().acknowledgeAlert('a1');
    useMissionStore.getState().clearAcknowledgedAlerts();
    expect(useMissionStore.getState().acknowledgedAlertIds).toEqual([]);
  });
});

// ─── Replay slice ─────────────────────────────────────────────────────────────

describe('missionStore — replay slice initial state', () => {
  beforeEach(resetStore);

  it('isReplaying defaults to false', () => {
    expect(useMissionStore.getState().isReplaying).toBe(false);
  });

  it('replayPaused defaults to false', () => {
    expect(useMissionStore.getState().replayPaused).toBe(false);
  });

  it('replayIndex defaults to 0', () => {
    expect(useMissionStore.getState().replayIndex).toBe(0);
  });

  it('replaySpeed defaults to 1', () => {
    expect(useMissionStore.getState().replaySpeed).toBe(1);
  });

  it('replayHistory defaults to empty array', () => {
    expect(useMissionStore.getState().replayHistory).toEqual([]);
  });

  it('finalMissionState defaults to null', () => {
    expect(useMissionStore.getState().finalMissionState).toBeNull();
  });
});

describe('missionStore — replay recording via setMissionState', () => {
  beforeEach(resetStore);

  it('first setMissionState starts a new history with one frame', () => {
    useMissionStore.getState().setMissionState(MISSION_STATE);
    expect(useMissionStore.getState().replayHistory).toHaveLength(1);
  });

  it('subsequent setMissionState calls with same mission_id append frames', () => {
    useMissionStore.getState().setMissionState(MISSION_STATE);
    useMissionStore.getState().setMissionState(makeMissionState({ elapsed_seconds: 10 }));
    useMissionStore.getState().setMissionState(makeMissionState({ elapsed_seconds: 20 }));
    expect(useMissionStore.getState().replayHistory).toHaveLength(3);
  });

  it('new mission_id resets replayHistory', () => {
    useMissionStore.getState().setMissionState(MISSION_STATE);
    useMissionStore.getState().setMissionState(makeMissionState({ elapsed_seconds: 10 }));
    // Different mission_id → reset
    useMissionStore.getState().setMissionState(
      makeMissionState({ mission_id: 'new-mission-999', elapsed_seconds: 0 }),
    );
    expect(useMissionStore.getState().replayHistory).toHaveLength(1);
  });

  it('setMissionState during replay does not append to history', () => {
    useMissionStore.getState().setMissionState(MISSION_STATE);
    useMissionStore.getState().setMissionState(makeMissionState({ elapsed_seconds: 10 }));
    useMissionStore.getState().startReplay();
    const lengthBeforeWsUpdate = useMissionStore.getState().replayHistory.length;
    // Simulate WS push for the same mission while replaying — should be ignored
    useMissionStore.getState().setMissionState(makeMissionState({ elapsed_seconds: 20 }));
    expect(useMissionStore.getState().replayHistory).toHaveLength(lengthBeforeWsUpdate);
  });
});

describe('missionStore — startReplay', () => {
  beforeEach(resetStore);

  it('sets isReplaying to true', () => {
    useMissionStore.getState().setMissionState(MISSION_STATE);
    useMissionStore.getState().startReplay();
    expect(useMissionStore.getState().isReplaying).toBe(true);
  });

  it('sets replayIndex to 0', () => {
    useMissionStore.getState().setMissionState(MISSION_STATE);
    useMissionStore.getState().startReplay();
    expect(useMissionStore.getState().replayIndex).toBe(0);
  });

  it('saves finalMissionState before switching to frame 0', () => {
    useMissionStore.getState().setMissionState(MISSION_STATE);
    useMissionStore.getState().setMissionState(makeMissionState({ elapsed_seconds: 50 }));
    useMissionStore.getState().startReplay();
    expect(useMissionStore.getState().finalMissionState?.elapsed_seconds).toBe(50);
  });

  it('sets missionState to first frame', () => {
    useMissionStore.getState().setMissionState(MISSION_STATE);
    useMissionStore.getState().setMissionState(makeMissionState({ elapsed_seconds: 50 }));
    useMissionStore.getState().startReplay();
    expect(useMissionStore.getState().missionState?.elapsed_seconds).toBe(42);
  });

  it('does nothing if replayHistory is empty', () => {
    useMissionStore.getState().startReplay();
    expect(useMissionStore.getState().isReplaying).toBe(false);
  });
});

describe('missionStore — stepReplay', () => {
  beforeEach(() => {
    resetStore();
    useMissionStore.getState().setMissionState(MISSION_STATE);
    useMissionStore.getState().setMissionState(makeMissionState({ elapsed_seconds: 10 }));
    useMissionStore.getState().setMissionState(makeMissionState({ elapsed_seconds: 20 }));
    useMissionStore.getState().startReplay();
  });

  it('advances replayIndex by 1', () => {
    useMissionStore.getState().stepReplay();
    expect(useMissionStore.getState().replayIndex).toBe(1);
  });

  it('updates missionState to the next frame', () => {
    useMissionStore.getState().stepReplay();
    expect(useMissionStore.getState().missionState?.elapsed_seconds).toBe(10);
  });

  it('auto-pauses when reaching the last frame', () => {
    useMissionStore.getState().stepReplay();
    useMissionStore.getState().stepReplay();
    useMissionStore.getState().stepReplay(); // one past last — should auto-pause
    expect(useMissionStore.getState().replayPaused).toBe(true);
  });

  it('does not advance when paused', () => {
    useMissionStore.getState().pauseReplay();
    useMissionStore.getState().stepReplay();
    expect(useMissionStore.getState().replayIndex).toBe(0);
  });
});

describe('missionStore — pauseReplay / resumeReplay', () => {
  beforeEach(() => {
    resetStore();
    useMissionStore.getState().setMissionState(MISSION_STATE);
    useMissionStore.getState().setMissionState(makeMissionState({ elapsed_seconds: 10 }));
    useMissionStore.getState().startReplay();
  });

  it('pauseReplay sets replayPaused to true', () => {
    useMissionStore.getState().pauseReplay();
    expect(useMissionStore.getState().replayPaused).toBe(true);
  });

  it('resumeReplay sets replayPaused to false', () => {
    useMissionStore.getState().pauseReplay();
    useMissionStore.getState().resumeReplay();
    expect(useMissionStore.getState().replayPaused).toBe(false);
  });
});

describe('missionStore — restartReplay', () => {
  beforeEach(() => {
    resetStore();
    useMissionStore.getState().setMissionState(MISSION_STATE);
    useMissionStore.getState().setMissionState(makeMissionState({ elapsed_seconds: 10 }));
    useMissionStore.getState().setMissionState(makeMissionState({ elapsed_seconds: 20 }));
    useMissionStore.getState().startReplay();
    useMissionStore.getState().stepReplay(); // advance to frame 1
    useMissionStore.getState().stepReplay(); // advance to frame 2
  });

  it('resets replayIndex to 0', () => {
    useMissionStore.getState().restartReplay();
    expect(useMissionStore.getState().replayIndex).toBe(0);
  });

  it('sets missionState to the first frame', () => {
    useMissionStore.getState().restartReplay();
    expect(useMissionStore.getState().missionState?.elapsed_seconds).toBe(42);
  });

  it('clears replayPaused if paused', () => {
    useMissionStore.getState().pauseReplay();
    useMissionStore.getState().restartReplay();
    expect(useMissionStore.getState().replayPaused).toBe(false);
  });
});

describe('missionStore — exitReplay', () => {
  beforeEach(() => {
    resetStore();
    useMissionStore.getState().setMissionState(MISSION_STATE);
    useMissionStore.getState().setMissionState(makeMissionState({ elapsed_seconds: 50 }));
    useMissionStore.getState().startReplay();
  });

  it('sets isReplaying to false', () => {
    useMissionStore.getState().exitReplay();
    expect(useMissionStore.getState().isReplaying).toBe(false);
  });

  it('restores finalMissionState as missionState', () => {
    useMissionStore.getState().exitReplay();
    expect(useMissionStore.getState().missionState?.elapsed_seconds).toBe(50);
  });

  it('clears finalMissionState', () => {
    useMissionStore.getState().exitReplay();
    expect(useMissionStore.getState().finalMissionState).toBeNull();
  });

  it('clears replayPaused', () => {
    useMissionStore.getState().pauseReplay();
    useMissionStore.getState().exitReplay();
    expect(useMissionStore.getState().replayPaused).toBe(false);
  });
});

describe('missionStore — setReplaySpeed', () => {
  beforeEach(resetStore);

  it('updates replaySpeed to 2', () => {
    useMissionStore.getState().setReplaySpeed(2 as ReplaySpeed);
    expect(useMissionStore.getState().replaySpeed).toBe(2);
  });

  it('updates replaySpeed to 0.5', () => {
    useMissionStore.getState().setReplaySpeed(0.5 as ReplaySpeed);
    expect(useMissionStore.getState().replaySpeed).toBe(0.5);
  });

  it('resets back to 1', () => {
    useMissionStore.getState().setReplaySpeed(2 as ReplaySpeed);
    useMissionStore.getState().setReplaySpeed(1 as ReplaySpeed);
    expect(useMissionStore.getState().replaySpeed).toBe(1);
  });
});
