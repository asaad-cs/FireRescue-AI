import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TacticalMap } from '@/components/dashboard/TacticalMap';
import { HazardLevel, type DroneState, type ZoneState } from '@/types/mission';

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeZone(overrides: Partial<ZoneState> = {}): ZoneState {
  return {
    zone_id: '0_0_1',
    label: 'A1',
    grid_x: 0,
    grid_y: 0,
    hazard_level: HazardLevel.CLEAR,
    victim_probability: 0,
    last_observed_at: null,
    ...overrides,
  };
}

const NO_DRONE: DroneState | null = null;

function renderMap(
  zoneStates: Record<string, ZoneState> = {},
  droneState: DroneState | null = NO_DRONE,
  exploredPct = 0,
  isStale = false,
) {
  return render(
    <TacticalMap
      zoneStates={zoneStates}
      droneState={droneState}
      exploredPercentage={exploredPct}
      isStale={isStale}
    />,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('TacticalMap — basic rendering', () => {
  it('renders without crashing', () => {
    expect(() => renderMap()).not.toThrow();
  });

  it('has the correct testid', () => {
    renderMap();
    expect(screen.getByTestId('tactical-map')).toBeInTheDocument();
  });

  it('renders a 5×4 = 20 cell grid', () => {
    renderMap();
    // All 20 zone cells should be present (unobserved by default)
    for (let row = 0; row < 4; row++) {
      for (let col = 0; col < 5; col++) {
        expect(screen.getByTestId(`zone-cell-${col}-${row}`)).toBeInTheDocument();
      }
    }
  });

  it('shows BUILDING MAP heading', () => {
    renderMap();
    expect(screen.getByText('BUILDING MAP')).toBeInTheDocument();
  });

  it('shows 0/20 zones when no zone states', () => {
    renderMap();
    expect(screen.getByText(/0\/20 zones/)).toBeInTheDocument();
  });

  it('shows correct explored percentage', () => {
    renderMap({}, null, 55);
    expect(screen.getByText(/55% explored/)).toBeInTheDocument();
  });

  it('shows STALE indicator when data is stale', () => {
    renderMap({}, null, 0, true);
    expect(screen.getByText('STALE')).toBeInTheDocument();
  });

  it('does not show STALE when data is fresh', () => {
    renderMap({}, null, 0, false);
    expect(screen.queryByText('STALE')).not.toBeInTheDocument();
  });
});

describe('TacticalMap — zone states', () => {
  it('renders visited zone with correct label', () => {
    const zones = { '2_1_1': makeZone({ zone_id: '2_1_1', label: 'C2', grid_x: 2, grid_y: 1 }) };
    renderMap(zones);
    // C2 label should appear in the zone cell
    const cell = screen.getByTestId('zone-cell-2-1');
    expect(cell).toHaveTextContent('C2');
  });

  it('renders unvisited zone with expected label', () => {
    renderMap();
    // Cell (3,2) = D3 — unvisited, should still show derived label
    const cell = screen.getByTestId('zone-cell-3-2');
    expect(cell).toHaveTextContent('D3');
  });

  it('shows hazard abbreviation for non-UNOBSERVED zones', () => {
    const zones = {
      '0_0_1': makeZone({ hazard_level: HazardLevel.CRITICAL }),
    };
    renderMap(zones);
    const cell = screen.getByTestId('zone-cell-0-0');
    expect(cell).toHaveTextContent('CRIT');
  });

  it('does not show abbreviation for UNOBSERVED zones', () => {
    renderMap();
    const cell = screen.getByTestId('zone-cell-0-0');
    expect(cell).not.toHaveTextContent('CLR');
    expect(cell).not.toHaveTextContent('CRIT');
  });

  it('shows correct count when zones are visited', () => {
    const zones: Record<string, ZoneState> = {};
    for (let i = 0; i < 5; i++) {
      zones[`${i}_0_1`] = makeZone({ zone_id: `${i}_0_1`, grid_x: i, grid_y: 0 });
    }
    renderMap(zones);
    expect(screen.getByText(/5\/20 zones/)).toBeInTheDocument();
  });
});

describe('TacticalMap — drone marker', () => {
  it('marks the drone cell with an accessible ring', () => {
    const droneState: DroneState = {
      drone_id: 'd1',
      x: 2,
      y: 1,
      floor: 1,
      heading: 0,
      last_seen: null,
    };
    renderMap({}, droneState);
    const cell = screen.getByTestId('zone-cell-2-1');
    expect(cell).toHaveAttribute('aria-label', expect.stringContaining('drone here'));
  });

  it('does not mark non-drone cells', () => {
    const droneState: DroneState = {
      drone_id: 'd1', x: 2, y: 1, floor: 1, heading: 0, last_seen: null,
    };
    renderMap({}, droneState);
    const otherCell = screen.getByTestId('zone-cell-0-0');
    expect(otherCell).not.toHaveAttribute('aria-label', expect.stringContaining('drone here'));
  });

  it('shows drone location in header', () => {
    const droneState: DroneState = {
      drone_id: 'd1', x: 1, y: 2, floor: 1, heading: 0, last_seen: null,
    };
    renderMap({}, droneState);
    expect(screen.getByText(/Drone →/)).toBeInTheDocument();
  });
});

describe('TacticalMap — victim signals', () => {
  it('marks zone with victim signal indicator when probability >= 0.3', () => {
    const zones = {
      '1_1_1': makeZone({
        zone_id: '1_1_1',
        grid_x: 1,
        grid_y: 1,
        victim_probability: 0.65,
      }),
    };
    renderMap(zones);
    const cell = screen.getByTestId('zone-cell-1-1');
    expect(cell).toHaveAttribute('aria-label', expect.stringContaining('victim signal'));
  });

  it('does not mark zone below threshold', () => {
    const zones = {
      '0_0_1': makeZone({ victim_probability: 0.15 }),
    };
    renderMap(zones);
    const cell = screen.getByTestId('zone-cell-0-0');
    expect(cell).not.toHaveAttribute('aria-label', expect.stringContaining('victim signal'));
  });
});

describe('TacticalMap — legend', () => {
  it('renders the map legend', () => {
    renderMap();
    expect(screen.getByTestId('map-legend')).toBeInTheDocument();
  });

  it('legend contains all hazard level labels', () => {
    renderMap();
    expect(screen.getByText('Clear')).toBeInTheDocument();
    expect(screen.getByText('Critical')).toBeInTheDocument();
    expect(screen.getByText('Unobserved')).toBeInTheDocument();
  });

  it('legend contains drone and victim signal labels', () => {
    renderMap();
    expect(screen.getByText('Drone')).toBeInTheDocument();
    expect(screen.getByText('Victim Signal')).toBeInTheDocument();
  });
});
