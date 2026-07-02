import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TacticalMap } from '@/components/placeholders/TacticalMap';
import { AlertPanel } from '@/components/placeholders/AlertPanel';
import { MissionStatistics } from '@/components/placeholders/MissionStatistics';
import { DroneStatus } from '@/components/placeholders/DroneStatus';
import { VictimSignals } from '@/components/placeholders/VictimSignals';
import { MissionTimeline } from '@/components/placeholders/MissionTimeline';
import { MissionControls } from '@/components/placeholders/MissionControls';
import { ConnectionIndicator } from '@/components/placeholders/ConnectionIndicator';
import { MissionStatus, HazardLevel } from '@/types/mission';

// ─── TacticalMap ──────────────────────────────────────────────────────────────

describe('TacticalMap', () => {
  it('renders without crashing', () => {
    render(
      <TacticalMap
        zoneStates={{}}
        droneState={null}
        exploredPercentage={0}
        isStale={false}
      />,
    );
    expect(screen.getByTestId('tactical-map')).toBeInTheDocument();
  });

  it('shows stale indicator when isStale is true', () => {
    render(
      <TacticalMap
        zoneStates={{}}
        droneState={null}
        exploredPercentage={0}
        isStale={true}
      />,
    );
    expect(screen.getByText(/stale/i)).toBeInTheDocument();
  });

  it('shows zone count when zoneStates is non-empty', () => {
    const zones = {
      '1_1_1': {
        zone_id: '1_1_1',
        label: 'A1',
        grid_x: 0,
        grid_y: 0,
        hazard_level: HazardLevel.CLEAR,
        victim_probability: 0,
        last_observed_at: null,
      },
    };
    render(
      <TacticalMap
        zoneStates={zones}
        droneState={null}
        exploredPercentage={10}
        isStale={false}
      />,
    );
    expect(screen.getByText(/1 zone/i)).toBeInTheDocument();
  });

  it('shows drone position when droneState is provided', () => {
    render(
      <TacticalMap
        zoneStates={{}}
        droneState={{ drone_id: 'd1', x: 2, y: 3, floor: 1, heading: 0, last_seen: null }}
        exploredPercentage={0}
        isStale={false}
      />,
    );
    expect(screen.getByText(/2,3/)).toBeInTheDocument();
  });
});

// ─── AlertPanel ───────────────────────────────────────────────────────────────

describe('AlertPanel', () => {
  it('renders without crashing', () => {
    render(<AlertPanel alerts={[]} alertCount={0} />);
    expect(screen.getByTestId('alert-panel')).toBeInTheDocument();
  });

  it('displays the alert count', () => {
    render(<AlertPanel alerts={[]} alertCount={4} />);
    expect(screen.getByText('(4)')).toBeInTheDocument();
  });

  it('shows no-alerts message when alerts list is empty', () => {
    render(<AlertPanel alerts={[]} alertCount={0} />);
    expect(screen.getByText(/no alerts/i)).toBeInTheDocument();
  });
});

// ─── MissionStatistics ────────────────────────────────────────────────────────

describe('MissionStatistics', () => {
  it('renders without crashing with null state', () => {
    render(<MissionStatistics missionState={null} />);
    expect(screen.getByTestId('mission-statistics')).toBeInTheDocument();
  });
});

// ─── DroneStatus ──────────────────────────────────────────────────────────────

describe('DroneStatus', () => {
  it('renders without crashing', () => {
    render(
      <DroneStatus
        droneState={null}
        latestReadings={{ temperature: null, co_level: null, smoke_density: null }}
        isStale={false}
      />,
    );
    expect(screen.getByTestId('drone-status')).toBeInTheDocument();
  });

  it('shows stale indicator when isStale is true', () => {
    render(
      <DroneStatus
        droneState={null}
        latestReadings={{ temperature: null, co_level: null, smoke_density: null }}
        isStale={true}
      />,
    );
    expect(screen.getByText(/stale/i)).toBeInTheDocument();
  });

  it('shows temperature when reading is present', () => {
    render(
      <DroneStatus
        droneState={null}
        latestReadings={{ temperature: 42.5, co_level: null, smoke_density: null }}
        isStale={false}
      />,
    );
    expect(screen.getByText(/42\.5/)).toBeInTheDocument();
  });
});

// ─── VictimSignals ────────────────────────────────────────────────────────────

describe('VictimSignals', () => {
  it('renders without crashing', () => {
    render(<VictimSignals zoneStates={{}} victimSignalCount={0} />);
    expect(screen.getByTestId('victim-signals')).toBeInTheDocument();
  });

  it('shows no-detections message when no zones above threshold', () => {
    render(<VictimSignals zoneStates={{}} victimSignalCount={0} />);
    expect(screen.getByText(/no detections/i)).toBeInTheDocument();
  });

  it('shows signal count when zones above threshold exist', () => {
    const zones = {
      z1: {
        zone_id: 'z1',
        label: 'A1',
        grid_x: 0,
        grid_y: 0,
        hazard_level: HazardLevel.CLEAR,
        victim_probability: 0.75,
        last_observed_at: null,
      },
    };
    render(<VictimSignals zoneStates={zones} victimSignalCount={1} />);
    expect(screen.getByText(/1 signal/i)).toBeInTheDocument();
  });
});

// ─── MissionTimeline ─────────────────────────────────────────────────────────

describe('MissionTimeline', () => {
  it('renders without crashing', () => {
    render(<MissionTimeline alerts={[]} status={MissionStatus.IDLE} />);
    expect(screen.getByTestId('mission-timeline')).toBeInTheDocument();
  });

  it('shows MISSION TIMELINE label', () => {
    render(<MissionTimeline alerts={[]} status={MissionStatus.IDLE} />);
    expect(screen.getByText('MISSION TIMELINE')).toBeInTheDocument();
  });
});

// ─── MissionControls ─────────────────────────────────────────────────────────

describe('MissionControls', () => {
  it('renders without crashing', () => {
    render(
      <MissionControls
        status={MissionStatus.IDLE}
        missionId=""
        elapsedSeconds={0}
      />,
    );
    expect(screen.getByTestId('mission-controls')).toBeInTheDocument();
  });

  it('shows mission ID when provided', () => {
    render(
      <MissionControls
        status={MissionStatus.ACTIVE}
        missionId="M-2026-001"
        elapsedSeconds={42}
      />,
    );
    expect(screen.getByText('M-2026-001')).toBeInTheDocument();
  });

  it('shows elapsed time when mission is active', () => {
    render(
      <MissionControls
        status={MissionStatus.ACTIVE}
        missionId="M-001"
        elapsedSeconds={90}
      />,
    );
    // 90 seconds = 00:01:30
    expect(screen.getByText('00:01:30')).toBeInTheDocument();
  });
});

// ─── ConnectionIndicator ──────────────────────────────────────────────────────

describe('ConnectionIndicator', () => {
  it('renders without crashing', () => {
    render(<ConnectionIndicator wsStatus="disconnected" reconnectAttempts={0} />);
    expect(screen.getByTestId('connection-indicator')).toBeInTheDocument();
  });

  it('shows CONNECTED label when status is connected', () => {
    render(<ConnectionIndicator wsStatus="connected" reconnectAttempts={0} />);
    expect(screen.getByText('CONNECTED')).toBeInTheDocument();
  });

  it('shows DISCONNECTED label when status is disconnected', () => {
    render(<ConnectionIndicator wsStatus="disconnected" reconnectAttempts={0} />);
    expect(screen.getByText('DISCONNECTED')).toBeInTheDocument();
  });

  it('shows RECONNECTING label when status is reconnecting', () => {
    render(<ConnectionIndicator wsStatus="reconnecting" reconnectAttempts={2} />);
    expect(screen.getByText('RECONNECTING')).toBeInTheDocument();
  });

  it('shows reconnect attempt count when reconnecting', () => {
    render(<ConnectionIndicator wsStatus="reconnecting" reconnectAttempts={3} />);
    expect(screen.getByText('#3')).toBeInTheDocument();
  });

  it('has role=status for accessibility', () => {
    render(<ConnectionIndicator wsStatus="connected" reconnectAttempts={0} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
