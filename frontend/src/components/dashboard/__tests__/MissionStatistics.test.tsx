import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MissionStatistics } from '@/components/dashboard/MissionStatistics';
import { MissionStatus, type MissionState } from '@/types/mission';

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeState(overrides: Partial<MissionState> = {}): MissionState {
  return {
    mission_id:          'mission-abc',
    status:              MissionStatus.ACTIVE,
    explored_percentage: 50,
    elapsed_seconds:     125,
    alert_count:         3,
    victim_signal_count: 1,
    active_alerts:       [],
    drone_state:         null,
    latest_readings:     { temperature: null, co_level: null, smoke_density: null },
    zone_states:         {},
    ...overrides,
  } as MissionState;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('MissionStatistics', () => {
  it('renders data-testid="mission-statistics"', () => {
    render(<MissionStatistics missionState={null} />);
    expect(screen.getByTestId('mission-statistics')).toBeInTheDocument();
  });

  it('shows em-dashes for all values when missionState is null', () => {
    render(<MissionStatistics missionState={null} />);
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(4);
  });

  it('shows formatted explored percentage', () => {
    render(<MissionStatistics missionState={makeState({ explored_percentage: 75 })} />);
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('shows formatted elapsed time as HH:MM:SS', () => {
    // 125 seconds = 00:02:05
    render(<MissionStatistics missionState={makeState({ elapsed_seconds: 125 })} />);
    expect(screen.getByText('00:02:05')).toBeInTheDocument();
  });

  it('shows alert count', () => {
    render(<MissionStatistics missionState={makeState({ alert_count: 5 })} />);
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('shows victim signal count', () => {
    render(<MissionStatistics missionState={makeState({ victim_signal_count: 2 })} />);
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('shows mission status badge', () => {
    render(<MissionStatistics missionState={makeState({ status: MissionStatus.ACTIVE })} />);
    expect(screen.getByText(MissionStatus.ACTIVE)).toBeInTheDocument();
  });

  it('shows ENDED status badge for ended mission', () => {
    render(<MissionStatistics missionState={makeState({ status: MissionStatus.ENDED })} />);
    expect(screen.getByText(MissionStatus.ENDED)).toBeInTheDocument();
  });

  it('does not show status badge when missionState is null', () => {
    render(<MissionStatistics missionState={null} />);
    expect(screen.queryByText(MissionStatus.ACTIVE)).not.toBeInTheDocument();
    expect(screen.queryByText(MissionStatus.IDLE)).not.toBeInTheDocument();
  });

  it('shows zero alert count correctly', () => {
    render(<MissionStatistics missionState={makeState({ alert_count: 0 })} />);
    expect(screen.getByText('0')).toBeInTheDocument();
  });
});
