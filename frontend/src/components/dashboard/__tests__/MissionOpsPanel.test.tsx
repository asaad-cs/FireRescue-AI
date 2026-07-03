/** MissionOpsPanel tests — operations summary derived from MissionState. */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MissionOpsPanel } from '@/components/dashboard/MissionOpsPanel';
import {
  ConnectionStatus,
  HazardLevel,
  MissionStatus,
  type MissionState,
  type ZoneState,
} from '@/types/mission';

function makeZone(overrides: Partial<ZoneState>): ZoneState {
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

function makeState(overrides: Partial<MissionState> = {}): MissionState {
  return {
    mission_id: 'm-1',
    status: MissionStatus.ACTIVE,
    started_at: null,
    ended_at: null,
    elapsed_seconds: 83,
    drone_state: null,
    zone_states: {
      a: makeZone({ zone_id: 'a' }),
      b: makeZone({ zone_id: 'b', hazard_level: HazardLevel.CRITICAL }),
      c: makeZone({ zone_id: 'c', hazard_level: HazardLevel.MODERATE }),
      d: makeZone({ zone_id: 'd', hazard_level: HazardLevel.LOW }),
    },
    active_alerts: [],
    latest_readings: { temperature: null, co_level: null, smoke_density: null },
    alert_count: 0,
    victim_signal_count: 2,
    explored_percentage: 20, // 4 scanned of 20 total
    connection_status: ConnectionStatus.CONNECTED,
    vision: {
      frame_id: 'f',
      zone_id: 'b',
      timestamp: null,
      detector_name: 'yolo',
      model_name: 'detector.onnx',
      frame_number: 4,
      image_base64: '',
      image_width: 640,
      image_height: 640,
      inference_ms: 21.7,
      confidence_threshold: 0.25,
      detections: [],
    },
    ...overrides,
  };
}

describe('MissionOpsPanel', () => {
  it('shows the mission status chip and timer', () => {
    render(<MissionOpsPanel missionState={makeState()} />);
    expect(screen.getByText('ACTIVE')).toBeInTheDocument();
    expect(screen.getByText('00:01:23')).toBeInTheDocument();
  });

  it('derives rooms scanned and remaining from explored percentage', () => {
    render(<MissionOpsPanel missionState={makeState()} />);
    expect(screen.getByText('Rooms scanned').nextSibling).toHaveTextContent('4');
    expect(screen.getByText('Rooms remaining').nextSibling)
      .toHaveTextContent('16');
  });

  it('counts hazards of MODERATE and above', () => {
    render(<MissionOpsPanel missionState={makeState()} />);
    expect(screen.getByText('Hazards detected').nextSibling)
      .toHaveTextContent('2'); // CRITICAL + MODERATE, not LOW
  });

  it('shows victim count and AI facts from the vision frame', () => {
    render(<MissionOpsPanel missionState={makeState()} />);
    expect(screen.getByText('Victims detected').nextSibling)
      .toHaveTextContent('2');
    expect(screen.getByText('YOLO')).toBeInTheDocument();
    expect(screen.getByText('detector.onnx')).toBeInTheDocument();
    expect(screen.getByText('21.7 ms')).toBeInTheDocument();
    expect(screen.getByText('SIM-CAM-01')).toBeInTheDocument();
  });

  it('degrades gracefully without vision and without state', () => {
    render(
      <MissionOpsPanel missionState={makeState({ vision: null })} />
    );
    expect(screen.getByText('GROUND TRUTH')).toBeInTheDocument();
    expect(screen.getByText('no feed')).toBeInTheDocument();

    render(<MissionOpsPanel missionState={null} />);
    expect(screen.getAllByText('IDLE').length).toBeGreaterThan(0);
  });
});
