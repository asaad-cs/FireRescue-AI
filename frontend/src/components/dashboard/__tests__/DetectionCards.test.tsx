/** DetectionCards tests — per-class status, confidence, and indicators. */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DetectionCards } from '@/components/dashboard/DetectionCards';
import { type VisionFrame } from '@/types/mission';

function makeFrame(detections: VisionFrame['detections']): VisionFrame {
  return {
    frame_id: 'f-1',
    zone_id: '1_0_1',
    timestamp: null,
    detector_name: 'yolo',
    model_name: 'm.onnx',
    frame_number: 1,
    image_base64: 'Zm9v',
    image_width: 640,
    image_height: 640,
    inference_ms: 20,
    confidence_threshold: 0.25,
    detections,
  };
}

describe('DetectionCards', () => {
  it('renders one card per class', () => {
    render(<DetectionCards vision={null} />);
    expect(screen.getByTestId('detection-card-fire')).toBeInTheDocument();
    expect(screen.getByTestId('detection-card-smoke')).toBeInTheDocument();
    expect(screen.getByTestId('detection-card-person')).toBeInTheDocument();
    expect(screen.getByText('Fire')).toBeInTheDocument();
    expect(screen.getByText('Smoke')).toBeInTheDocument();
    expect(screen.getByText('Victim')).toBeInTheDocument();
  });

  it('shows NO FEED on every card when vision is null', () => {
    render(<DetectionCards vision={null} />);
    expect(screen.getAllByText('NO FEED')).toHaveLength(3);
  });

  it('shows DETECTED with the best confidence for present classes', () => {
    render(
      <DetectionCards
        vision={makeFrame([
          { class_name: 'fire', confidence: 0.61, bbox: [0, 0, 1, 1] },
          { class_name: 'fire', confidence: 0.94, bbox: [2, 2, 3, 3] },
        ])}
      />
    );
    expect(screen.getByTestId('detection-status-fire')).toHaveTextContent(
      'DETECTED ×2'
    );
    expect(screen.getByTestId('detection-card-fire')).toHaveTextContent('94%');
  });

  it('shows CLEAR for absent classes when a frame exists', () => {
    render(
      <DetectionCards
        vision={makeFrame([
          { class_name: 'fire', confidence: 0.9, bbox: [0, 0, 1, 1] },
        ])}
      />
    );
    expect(screen.getByTestId('detection-status-smoke')).toHaveTextContent(
      'CLEAR'
    );
    expect(screen.getByTestId('detection-status-person')).toHaveTextContent(
      'CLEAR'
    );
    expect(screen.getByTestId('detection-card-smoke')).toHaveTextContent('—');
  });

  it('person detections light up the Victim card', () => {
    render(
      <DetectionCards
        vision={makeFrame([
          { class_name: 'person', confidence: 0.85, bbox: [0, 0, 1, 1] },
        ])}
      />
    );
    const card = screen.getByTestId('detection-card-person');
    expect(card).toHaveTextContent('DETECTED');
    expect(card).toHaveTextContent('85%');
    expect(card.style.borderColor).toBe('rgb(59, 130, 246)');
  });
});
