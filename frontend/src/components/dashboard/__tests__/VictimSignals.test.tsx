import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VictimSignals } from '@/components/dashboard/VictimSignals';
import { HazardLevel, type ZoneState } from '@/types/mission';

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeZone(id: string, label: string, prob: number): ZoneState {
  return {
    zone_id: id,
    label,
    grid_x: 0,
    grid_y: 0,
    hazard_level: HazardLevel.CLEAR,
    victim_probability: prob,
    last_observed_at: null,
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('VictimSignals — basic rendering', () => {
  it('renders without crashing', () => {
    expect(() =>
      render(<VictimSignals zoneStates={{}} victimSignalCount={0} />),
    ).not.toThrow();
  });

  it('has correct testid', () => {
    render(<VictimSignals zoneStates={{}} victimSignalCount={0} />);
    expect(screen.getByTestId('victim-signals')).toBeInTheDocument();
  });

  it('shows VICTIM SIGNALS heading', () => {
    render(<VictimSignals zoneStates={{}} victimSignalCount={0} />);
    expect(screen.getByText('VICTIM SIGNALS')).toBeInTheDocument();
  });

  it('shows empty state when no zones above threshold', () => {
    render(<VictimSignals zoneStates={{}} victimSignalCount={0} />);
    expect(screen.getByText('No signals above threshold')).toBeInTheDocument();
  });
});

describe('VictimSignals — threshold filtering', () => {
  it('shows zone at exactly 0.30 threshold', () => {
    const zones = { 'z1': makeZone('z1', 'B2', 0.30) };
    render(<VictimSignals zoneStates={zones} victimSignalCount={1} />);
    expect(screen.getByTestId('victim-signal-z1')).toBeInTheDocument();
  });

  it('hides zone below 0.30 threshold', () => {
    const zones = { 'z1': makeZone('z1', 'B2', 0.29) };
    render(<VictimSignals zoneStates={zones} victimSignalCount={0} />);
    expect(screen.queryByTestId('victim-signal-z1')).not.toBeInTheDocument();
  });

  it('shows multiple zones above threshold', () => {
    const zones = {
      'z1': makeZone('z1', 'A1', 0.75),
      'z2': makeZone('z2', 'B2', 0.45),
      'z3': makeZone('z3', 'C3', 0.20), // below threshold
    };
    render(<VictimSignals zoneStates={zones} victimSignalCount={2} />);
    expect(screen.getByTestId('victim-signal-z1')).toBeInTheDocument();
    expect(screen.getByTestId('victim-signal-z2')).toBeInTheDocument();
    expect(screen.queryByTestId('victim-signal-z3')).not.toBeInTheDocument();
  });
});

describe('VictimSignals — display and language', () => {
  it('shows zone label', () => {
    const zones = { 'z1': makeZone('z1', 'D4', 0.65) };
    render(<VictimSignals zoneStates={zones} victimSignalCount={1} />);
    expect(screen.getByText('D4')).toBeInTheDocument();
  });

  it('shows probability as percentage', () => {
    const zones = { 'z1': makeZone('z1', 'A1', 0.65) };
    render(<VictimSignals zoneStates={zones} victimSignalCount={1} />);
    expect(screen.getByText('65%')).toBeInTheDocument();
  });

  it('shows count badge from victimSignalCount', () => {
    const zones = { 'z1': makeZone('z1', 'A1', 0.65) };
    render(<VictimSignals zoneStates={zones} victimSignalCount={3} />);
    expect(screen.getByText('3 detected')).toBeInTheDocument();
  });

  it('does not use "Victim Confirmed" language anywhere', () => {
    const zones = {
      'z1': makeZone('z1', 'A1', 0.95),
      'z2': makeZone('z2', 'B2', 0.85),
    };
    const { container } = render(
      <VictimSignals zoneStates={zones} victimSignalCount={2} />,
    );
    expect(container.textContent).not.toContain('Confirmed');
    expect(container.textContent).not.toContain('Detected');
  });
});

describe('VictimSignals — sort order', () => {
  it('sorts zones by probability descending', () => {
    const zones = {
      'low':  makeZone('low',  'A1', 0.40),
      'high': makeZone('high', 'B2', 0.80),
      'mid':  makeZone('mid',  'C3', 0.60),
    };
    render(<VictimSignals zoneStates={zones} victimSignalCount={3} />);
    const items = screen.getAllByRole('listitem');
    // First should be the highest probability zone (B2 = 80%)
    expect(items[0]).toHaveTextContent('B2');
    expect(items[1]).toHaveTextContent('C3');
    expect(items[2]).toHaveTextContent('A1');
  });
});

describe('VictimSignals — accessibility', () => {
  it('has an accessible list with a label', () => {
    render(<VictimSignals zoneStates={{}} victimSignalCount={0} />);
    expect(screen.getByRole('list', { name: /victim signal/i })).toBeInTheDocument();
  });

  it('each signal entry has an accessible aria-label', () => {
    const zones = { 'z1': makeZone('z1', 'E4', 0.70) };
    render(<VictimSignals zoneStates={zones} victimSignalCount={1} />);
    const item = screen.getByRole('listitem');
    expect(item).toHaveAttribute('aria-label', expect.stringContaining('E4'));
    expect(item).toHaveAttribute('aria-label', expect.stringContaining('70%'));
  });
});
