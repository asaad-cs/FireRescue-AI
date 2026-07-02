import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DroneStatus } from '@/components/dashboard/DroneStatus';
import { HazardLevel, type DroneState, type LatestReadings, type ZoneState } from '@/types/mission';

// ── Fixtures ──────────────────────────────────────────────────────────────────

const DRONE: DroneState = {
  drone_id: 'drone-1',
  x: 2,
  y: 1,
  floor: 1,
  heading: 90,
  last_seen: '2026-07-01T10:30:00Z',
};

const READINGS: LatestReadings = {
  temperature: 45.5,
  co_level: 120.0,
  smoke_density: 0.25,
};

const NULL_READINGS: LatestReadings = {
  temperature: null,
  co_level: null,
  smoke_density: null,
};

const ZONE_STATES: Record<string, ZoneState> = {
  '2_1_1': {
    zone_id: '2_1_1',
    label: 'C2',
    grid_x: 2,
    grid_y: 1,
    hazard_level: HazardLevel.MODERATE,
    victim_probability: 0,
    last_observed_at: null,
  },
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('DroneStatus — basic rendering', () => {
  it('renders without crashing', () => {
    expect(() =>
      render(<DroneStatus droneState={null} latestReadings={NULL_READINGS} zoneStates={{}} isStale={false} />),
    ).not.toThrow();
  });

  it('has correct testid', () => {
    render(<DroneStatus droneState={null} latestReadings={NULL_READINGS} zoneStates={{}} isStale={false} />);
    expect(screen.getByTestId('drone-status')).toBeInTheDocument();
  });

  it('shows DRONE STATUS heading', () => {
    render(<DroneStatus droneState={null} latestReadings={NULL_READINGS} zoneStates={{}} isStale={false} />);
    expect(screen.getByText('DRONE STATUS')).toBeInTheDocument();
  });

  it('shows no drone data message when droneState is null', () => {
    render(<DroneStatus droneState={null} latestReadings={NULL_READINGS} zoneStates={{}} isStale={false} />);
    expect(screen.getByText('No drone data')).toBeInTheDocument();
  });
});

describe('DroneStatus — with drone data', () => {
  it('shows drone grid coordinates', () => {
    render(<DroneStatus droneState={DRONE} latestReadings={READINGS} zoneStates={ZONE_STATES} isStale={false} />);
    expect(screen.getByText(/\(2,1\)/)).toBeInTheDocument();
  });

  it('shows zone label from zone_states', () => {
    render(<DroneStatus droneState={DRONE} latestReadings={READINGS} zoneStates={ZONE_STATES} isStale={false} />);
    expect(screen.getByText('C2')).toBeInTheDocument();
  });

  it('shows fallback zone label when zone not in states', () => {
    render(<DroneStatus droneState={DRONE} latestReadings={READINGS} zoneStates={{}} isStale={false} />);
    expect(screen.getByText('(2,1)')).toBeInTheDocument();
  });
});

describe('DroneStatus — sensor readings', () => {
  it('shows temperature reading', () => {
    render(<DroneStatus droneState={DRONE} latestReadings={READINGS} zoneStates={{}} isStale={false} />);
    expect(screen.getByText('45.5 °C')).toBeInTheDocument();
  });

  it('shows CO level reading', () => {
    render(<DroneStatus droneState={DRONE} latestReadings={READINGS} zoneStates={{}} isStale={false} />);
    expect(screen.getByText('120.0 ppm')).toBeInTheDocument();
  });

  it('shows smoke density reading', () => {
    render(<DroneStatus droneState={DRONE} latestReadings={READINGS} zoneStates={{}} isStale={false} />);
    expect(screen.getByText('25.0%')).toBeInTheDocument();
  });

  it('shows dash for null readings', () => {
    render(<DroneStatus droneState={DRONE} latestReadings={NULL_READINGS} zoneStates={{}} isStale={false} />);
    // Three dashes — one for each null reading
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(3);
  });

  it('shows SENSOR READINGS label', () => {
    render(<DroneStatus droneState={DRONE} latestReadings={READINGS} zoneStates={{}} isStale={false} />);
    expect(screen.getByText('SENSOR READINGS')).toBeInTheDocument();
  });

  it('renders progress bars for each sensor', () => {
    render(<DroneStatus droneState={DRONE} latestReadings={READINGS} zoneStates={{}} isStale={false} />);
    const bars = screen.getAllByRole('progressbar');
    expect(bars.length).toBe(3);
  });
});

describe('DroneStatus — stale indicator', () => {
  it('shows STALE badge when isStale is true', () => {
    render(<DroneStatus droneState={DRONE} latestReadings={READINGS} zoneStates={{}} isStale={true} />);
    expect(screen.getByText('STALE')).toBeInTheDocument();
  });

  it('hides STALE badge when isStale is false', () => {
    render(<DroneStatus droneState={DRONE} latestReadings={READINGS} zoneStates={{}} isStale={false} />);
    expect(screen.queryByText('STALE')).not.toBeInTheDocument();
  });
});
