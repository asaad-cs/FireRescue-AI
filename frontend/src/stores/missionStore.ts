/**
 * Zustand store — single source of truth for all application state.
 *
 * Four logical slices kept in one store:
 *   connection — WebSocket status and reconnect metadata
 *   mission    — the live MissionState received from the backend
 *   ui         — ephemeral UI state (panel focus, alert acknowledgements)
 *   replay     — recorded history and playback state
 *
 * Components select only the slices they need via shallow equality selectors
 * to avoid unnecessary re-renders.
 */

import { create } from 'zustand';
import type { MissionState } from '@/types/mission';
import type { WsStatus } from '@/services/websocket';

// ─── Replay speed type ────────────────────────────────────────────────────────

export type ReplaySpeed = 0.5 | 1 | 2;

// ─── Slice shapes ─────────────────────────────────────────────────────────────

interface ConnectionSlice {
  wsStatus: WsStatus;
  lastConnectedAt: string | null; // ISO 8601
  reconnectAttempts: number;

  setWsStatus: (status: WsStatus) => void;
  incrementReconnectAttempts: () => void;
  resetReconnectAttempts: () => void;
}

interface MissionSlice {
  missionState: MissionState | null;
  lastUpdatedAt: string | null; // ISO 8601

  setMissionState: (state: MissionState) => void;
  clearMissionState: () => void;
}

interface UISlice {
  isSidebarCollapsed: boolean;
  acknowledgedAlertIds: string[];

  toggleSidebar: () => void;
  acknowledgeAlert: (alertId: string) => void;
  clearAcknowledgedAlerts: () => void;
}

interface ReplaySlice {
  /** Ordered snapshots recorded from the live mission (oldest → newest). */
  replayHistory: MissionState[];
  /** True while playback is running (even if paused). */
  isReplaying: boolean;
  /** True when playback has been paused mid-replay. */
  replayPaused: boolean;
  /** Index into replayHistory of the currently displayed frame. */
  replayIndex: number;
  /** Playback speed multiplier (frames per second relative to 1x = 1 frame/s). */
  replaySpeed: ReplaySpeed;
  /** The real final MissionState; restored when user exits replay. */
  finalMissionState: MissionState | null;

  startReplay: () => void;
  pauseReplay: () => void;
  resumeReplay: () => void;
  /** Advance one frame — called on each tick by useReplayEngine. */
  stepReplay: () => void;
  restartReplay: () => void;
  exitReplay: () => void;
  setReplaySpeed: (speed: ReplaySpeed) => void;
}

// ─── Combined store type ──────────────────────────────────────────────────────

export type AppStore = ConnectionSlice & MissionSlice & UISlice & ReplaySlice;

// ─── Store ────────────────────────────────────────────────────────────────────

export const useMissionStore = create<AppStore>()((set) => ({
  // ── Connection slice ───────────────────────────────────────────────────── //
  wsStatus: 'disconnected',
  lastConnectedAt: null,
  reconnectAttempts: 0,

  setWsStatus: (status) =>
    set((state) => ({
      wsStatus: status,
      lastConnectedAt:
        status === 'connected' ? new Date().toISOString() : state.lastConnectedAt,
      reconnectAttempts:
        status === 'connected' ? 0 : state.reconnectAttempts,
    })),

  incrementReconnectAttempts: () =>
    set((state) => ({ reconnectAttempts: state.reconnectAttempts + 1 })),

  resetReconnectAttempts: () => set({ reconnectAttempts: 0 }),

  // ── Mission slice ─────────────────────────────────────────────────────── //
  missionState: null,
  lastUpdatedAt: null,

  setMissionState: (newState) =>
    set((prev) => {
      // A new mission_id means the backend started a fresh mission.
      // Reset replay state and begin a clean history.
      const isNewMission =
        prev.missionState === null ||
        prev.missionState.mission_id !== newState.mission_id;

      if (isNewMission) {
        return {
          missionState: newState,
          lastUpdatedAt: new Date().toISOString(),
          replayHistory: [newState],
          isReplaying: false,
          replayPaused: false,
          replayIndex: 0,
          finalMissionState: null,
        };
      }

      // During replay: ignore incoming WS messages for the same mission
      // (history is already complete; replay is driving missionState).
      if (prev.isReplaying) {
        return {};
      }

      // Live update — append to history.
      return {
        missionState: newState,
        lastUpdatedAt: new Date().toISOString(),
        replayHistory: [...prev.replayHistory, newState],
      };
    }),

  clearMissionState: () => set({ missionState: null, lastUpdatedAt: null }),

  // ── UI slice ──────────────────────────────────────────────────────────── //
  isSidebarCollapsed: false,
  acknowledgedAlertIds: [],

  toggleSidebar: () =>
    set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),

  acknowledgeAlert: (alertId) =>
    set((state) => ({
      acknowledgedAlertIds: state.acknowledgedAlertIds.includes(alertId)
        ? state.acknowledgedAlertIds
        : [...state.acknowledgedAlertIds, alertId],
    })),

  clearAcknowledgedAlerts: () => set({ acknowledgedAlertIds: [] }),

  // ── Replay slice ──────────────────────────────────────────────────────── //
  replayHistory: [],
  isReplaying: false,
  replayPaused: false,
  replayIndex: 0,
  replaySpeed: 1,
  finalMissionState: null,

  startReplay: () =>
    set((state) => {
      if (state.replayHistory.length === 0) return {};
      return {
        isReplaying: true,
        replayPaused: false,
        replayIndex: 0,
        finalMissionState: state.missionState,
        missionState: state.replayHistory[0],
      };
    }),

  pauseReplay: () => set({ replayPaused: true }),

  resumeReplay: () =>
    set((state) => {
      // If already at the last frame, restart from the beginning.
      if (state.replayIndex >= state.replayHistory.length - 1) {
        return {
          replayPaused: false,
          replayIndex: 0,
          missionState: state.replayHistory[0] ?? state.missionState,
        };
      }
      return { replayPaused: false };
    }),

  stepReplay: () =>
    set((state) => {
      if (!state.isReplaying || state.replayPaused) return {};
      const next = state.replayIndex + 1;
      if (next >= state.replayHistory.length) {
        // Reached the last frame — auto-pause so the user can see the result.
        return { replayPaused: true };
      }
      return {
        replayIndex: next,
        missionState: state.replayHistory[next],
      };
    }),

  restartReplay: () =>
    set((state) => ({
      replayIndex: 0,
      replayPaused: false,
      missionState: state.replayHistory[0] ?? state.missionState,
    })),

  exitReplay: () =>
    set((state) => ({
      isReplaying: false,
      replayPaused: false,
      missionState: state.finalMissionState ?? state.missionState,
      finalMissionState: null,
    })),

  setReplaySpeed: (speed) => set({ replaySpeed: speed }),
}));
