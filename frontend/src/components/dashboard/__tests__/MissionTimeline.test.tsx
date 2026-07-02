import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MissionTimeline } from '@/components/dashboard/MissionTimeline';
import { AlertLevel, AlertType, MissionStatus, type Alert } from '@/types/mission';

// ── Helpers ───────────────────────────────────────────────────────────────────

let counter = 0;

function makeAlert(overrides: Partial<Alert> = {}): Alert {
  return {
    alert_id: `evt-${++counter}`,
    mission_id: 'm1',
    zone_id: 'A1',
    alert_type: AlertType.HAZARD_ELEVATED,
    level: AlertLevel.INFO,
    message: 'Test event',
    triggered_at: new Date().toISOString(),
    ...overrides,
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('MissionTimeline — basic rendering', () => {
  it('renders without crashing', () => {
    expect(() =>
      render(<MissionTimeline alerts={[]} status={MissionStatus.IDLE} />),
    ).not.toThrow();
  });

  it('has correct testid', () => {
    render(<MissionTimeline alerts={[]} status={MissionStatus.IDLE} />);
    expect(screen.getByTestId('mission-timeline')).toBeInTheDocument();
  });

  it('shows empty state message when no alerts', () => {
    render(<MissionTimeline alerts={[]} status={MissionStatus.IDLE} />);
    expect(screen.getByText('No events recorded')).toBeInTheDocument();
  });

  it('shows current mission status', () => {
    render(<MissionTimeline alerts={[]} status={MissionStatus.ACTIVE} />);
    expect(screen.getByText('ACTIVE')).toBeInTheDocument();
  });

  it('shows TIMELINE label', () => {
    render(<MissionTimeline alerts={[]} status={MissionStatus.IDLE} />);
    expect(screen.getByText('TIMELINE')).toBeInTheDocument();
  });
});

describe('MissionTimeline — event chips', () => {
  it('renders one chip per alert', () => {
    const alerts = [makeAlert({ alert_id: 'a1' }), makeAlert({ alert_id: 'a2' })];
    render(<MissionTimeline alerts={alerts} status={MissionStatus.ACTIVE} />);
    expect(screen.getByTestId('timeline-event-a1')).toBeInTheDocument();
    expect(screen.getByTestId('timeline-event-a2')).toBeInTheDocument();
  });

  it('each chip shows the alert message', () => {
    const alerts = [makeAlert({ alert_id: 'e1', message: 'Hazard in B3' })];
    render(<MissionTimeline alerts={alerts} status={MissionStatus.ACTIVE} />);
    expect(screen.getByText('Hazard in B3')).toBeInTheDocument();
  });

  it('shows level abbreviation in chip', () => {
    const alerts = [makeAlert({ alert_id: 'e2', level: AlertLevel.CRITICAL })];
    render(<MissionTimeline alerts={alerts} status={MissionStatus.ACTIVE} />);
    expect(screen.getByText('CRT')).toBeInTheDocument();
  });

  it('shows EMERGENCY abbreviation as EMG', () => {
    const alerts = [makeAlert({ alert_id: 'e3', level: AlertLevel.EMERGENCY })];
    render(<MissionTimeline alerts={alerts} status={MissionStatus.ACTIVE} />);
    expect(screen.getByText('EMG')).toBeInTheDocument();
  });

  it('chips have accessible aria-labels', () => {
    const alerts = [makeAlert({ alert_id: 'e4', message: 'Zone A1 critical' })];
    render(<MissionTimeline alerts={alerts} status={MissionStatus.ACTIVE} />);
    const chip = screen.getByTestId('timeline-event-e4');
    expect(chip).toHaveAttribute('aria-label', expect.stringContaining('Zone A1 critical'));
  });
});

describe('MissionTimeline — sort order', () => {
  it('sorts events oldest to newest (left to right)', () => {
    const older = makeAlert({
      alert_id: 'old',
      message: 'Older event',
      triggered_at: '2026-07-01T10:00:00Z',
    });
    const newer = makeAlert({
      alert_id: 'new',
      message: 'Newer event',
      triggered_at: '2026-07-01T10:05:00Z',
    });
    render(<MissionTimeline alerts={[newer, older]} status={MissionStatus.ACTIVE} />);
    const chips = screen.getAllByRole('listitem');
    expect(chips[0]).toHaveTextContent('Older event');
    expect(chips[1]).toHaveTextContent('Newer event');
  });
});
