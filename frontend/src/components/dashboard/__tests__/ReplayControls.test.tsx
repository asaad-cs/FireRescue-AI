import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ReplayControls } from '@/components/dashboard/ReplayControls';
import { useMissionStore } from '@/stores/missionStore';
import { MissionStatus, ConnectionStatus, type MissionState } from '@/types/mission';

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeState(seq: number = 0): MissionState {
  return {
    mission_id: 'replay-test-001',
    status: MissionStatus.ACTIVE,
    started_at: '2026-07-01T10:00:00Z',
    ended_at: null,
    elapsed_seconds: seq * 5,
    drone_state: {
      drone_id: 'drone-1',
      x: seq % 5,
      y: seq % 4,
      floor: 1,
      heading: 0,
      last_seen: '2026-07-01T10:00:00Z',
    },
    zone_states: {},
    active_alerts: [],
    latest_readings: { temperature: 25.0, co_level: 5.0, smoke_density: 0.02 },
    alert_count: 0,
    victim_signal_count: 0,
    explored_percentage: seq * 10,
    connection_status: ConnectionStatus.CONNECTED,
  };
}

/** Feed 5 frames into the store and start replay. */
function activateReplay() {
  const store = useMissionStore.getState();
  // First frame starts a new mission (prev.missionState is null after resetStore)
  store.setMissionState(makeState(0));
  for (let i = 1; i <= 4; i++) {
    store.setMissionState(makeState(i));
  }
  store.startReplay();
}

/** Return store to a clean pre-replay state. */
function resetStore() {
  const store = useMissionStore.getState();
  store.exitReplay();
  store.clearMissionState();
  store.setReplaySpeed(1);
}

// ── Visibility ────────────────────────────────────────────────────────────────

describe('ReplayControls — visibility', () => {
  beforeEach(resetStore);

  it('renders nothing when not replaying', () => {
    render(<ReplayControls />);
    expect(screen.queryByTestId('replay-controls')).not.toBeInTheDocument();
  });

  it('renders the panel when replaying', () => {
    activateReplay();
    render(<ReplayControls />);
    expect(screen.getByTestId('replay-controls')).toBeInTheDocument();
  });

  it('has correct ARIA region label', () => {
    activateReplay();
    render(<ReplayControls />);
    expect(screen.getByRole('region', { name: /replay controls/i })).toBeInTheDocument();
  });

  it('shows the REPLAY label text', () => {
    activateReplay();
    render(<ReplayControls />);
    expect(screen.getByText('REPLAY')).toBeInTheDocument();
  });
});

// ── Frame counter ─────────────────────────────────────────────────────────────

describe('ReplayControls — frame counter', () => {
  beforeEach(() => {
    resetStore();
    activateReplay();
  });

  it('renders the frame counter', () => {
    render(<ReplayControls />);
    expect(screen.getByTestId('replay-frame-counter')).toBeInTheDocument();
  });

  it('shows 1/5 at the start of a 5-frame replay', () => {
    render(<ReplayControls />);
    expect(screen.getByTestId('replay-frame-counter')).toHaveTextContent('1/5');
  });

  it('frame counter has accessible aria-label', () => {
    render(<ReplayControls />);
    expect(screen.getByTestId('replay-frame-counter')).toHaveAttribute(
      'aria-label',
      'Frame 1 of 5',
    );
  });
});

// ── Speed controls ────────────────────────────────────────────────────────────

describe('ReplayControls — speed controls', () => {
  beforeEach(() => {
    resetStore();
    activateReplay();
  });

  it('renders all three speed buttons', () => {
    render(<ReplayControls />);
    expect(screen.getByTestId('replay-speed-0.5')).toBeInTheDocument();
    expect(screen.getByTestId('replay-speed-1')).toBeInTheDocument();
    expect(screen.getByTestId('replay-speed-2')).toBeInTheDocument();
  });

  it('clicking 2× sets replaySpeed to 2 in the store', () => {
    render(<ReplayControls />);
    fireEvent.click(screen.getByTestId('replay-speed-2'));
    expect(useMissionStore.getState().replaySpeed).toBe(2);
  });

  it('clicking 0.5× sets replaySpeed to 0.5', () => {
    render(<ReplayControls />);
    fireEvent.click(screen.getByTestId('replay-speed-0.5'));
    expect(useMissionStore.getState().replaySpeed).toBe(0.5);
  });

  it('1× button is pressed by default', () => {
    render(<ReplayControls />);
    expect(screen.getByTestId('replay-speed-1')).toHaveAttribute('aria-pressed', 'true');
  });

  it('non-active speed buttons are not pressed', () => {
    render(<ReplayControls />);
    expect(screen.getByTestId('replay-speed-0.5')).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByTestId('replay-speed-2')).toHaveAttribute('aria-pressed', 'false');
  });
});

// ── Playback buttons (playing state) ─────────────────────────────────────────

describe('ReplayControls — playback buttons (playing)', () => {
  beforeEach(() => {
    resetStore();
    activateReplay();
  });

  it('shows PAUSE button when playing', () => {
    render(<ReplayControls />);
    expect(screen.getByTestId('btn-replay-pause')).toBeInTheDocument();
  });

  it('does not show RESUME when playing', () => {
    render(<ReplayControls />);
    expect(screen.queryByTestId('btn-replay-resume')).not.toBeInTheDocument();
  });

  it('clicking PAUSE sets replayPaused to true', () => {
    render(<ReplayControls />);
    fireEvent.click(screen.getByTestId('btn-replay-pause'));
    expect(useMissionStore.getState().replayPaused).toBe(true);
  });

  it('shows RESTART button', () => {
    render(<ReplayControls />);
    expect(screen.getByTestId('btn-replay-restart')).toBeInTheDocument();
  });

  it('shows EXIT button', () => {
    render(<ReplayControls />);
    expect(screen.getByTestId('btn-replay-exit')).toBeInTheDocument();
  });

  it('clicking EXIT sets isReplaying to false', () => {
    render(<ReplayControls />);
    fireEvent.click(screen.getByTestId('btn-replay-exit'));
    expect(useMissionStore.getState().isReplaying).toBe(false);
  });

  it('clicking RESTART resets replayIndex to 0', () => {
    useMissionStore.getState().stepReplay();
    render(<ReplayControls />);
    fireEvent.click(screen.getByTestId('btn-replay-restart'));
    expect(useMissionStore.getState().replayIndex).toBe(0);
  });
});

// ── Playback buttons (paused state) ──────────────────────────────────────────

describe('ReplayControls — playback buttons (paused)', () => {
  beforeEach(() => {
    resetStore();
    activateReplay();
    useMissionStore.getState().pauseReplay();
  });

  it('shows RESUME button when paused', () => {
    render(<ReplayControls />);
    expect(screen.getByTestId('btn-replay-resume')).toBeInTheDocument();
  });

  it('does not show PAUSE button when paused', () => {
    render(<ReplayControls />);
    expect(screen.queryByTestId('btn-replay-pause')).not.toBeInTheDocument();
  });

  it('clicking RESUME sets replayPaused to false', () => {
    render(<ReplayControls />);
    fireEvent.click(screen.getByTestId('btn-replay-resume'));
    expect(useMissionStore.getState().replayPaused).toBe(false);
  });
});

// ── Progress bar ──────────────────────────────────────────────────────────────

describe('ReplayControls — progress bar', () => {
  beforeEach(() => {
    resetStore();
    activateReplay();
  });

  it('renders the progress bar', () => {
    render(<ReplayControls />);
    expect(screen.getByTestId('replay-progress-bar')).toBeInTheDocument();
  });

  it('starts at 0% when at frame 0', () => {
    render(<ReplayControls />);
    expect(screen.getByTestId('replay-progress-bar')).toHaveStyle({ width: '0%' });
  });
});

// ── Accessibility ─────────────────────────────────────────────────────────────

describe('ReplayControls — accessibility', () => {
  beforeEach(() => {
    resetStore();
    activateReplay();
  });

  it('PAUSE button has accessible label', () => {
    render(<ReplayControls />);
    expect(screen.getByRole('button', { name: /pause replay/i })).toBeInTheDocument();
  });

  it('RESTART button has accessible label', () => {
    render(<ReplayControls />);
    expect(screen.getByRole('button', { name: /restart replay/i })).toBeInTheDocument();
  });

  it('EXIT button has accessible label', () => {
    render(<ReplayControls />);
    expect(screen.getByRole('button', { name: /exit replay/i })).toBeInTheDocument();
  });
});
