/**
 * MissionCamera tests — media abstraction, detection overlay, telemetry,
 * history, and the no-inference fallback. Ports and extends the Phase 8G
 * AIVisionPanel coverage (that panel was superseded by MissionCamera).
 */
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  CameraMedia,
  MissionCamera,
  classColor,
} from '@/components/dashboard/MissionCamera';
import { type VisionFrame } from '@/types/mission';

function makeFrame(overrides: Partial<VisionFrame> = {}): VisionFrame {
  return {
    frame_id: 'f-1',
    zone_id: '2_3_1',
    timestamp: '2026-07-03T08:00:00Z',
    detector_name: 'yolo',
    model_name: 'firerescue-detector-20260703.onnx',
    frame_number: 7,
    image_base64: 'Zm9vYmFy',
    image_width: 640,
    image_height: 480,
    inference_ms: 23.4,
    confidence_threshold: 0.25,
    detections: [
      { class_name: 'fire',   confidence: 0.94, bbox: [64, 48, 320, 240] },
      { class_name: 'smoke',  confidence: 0.81, bbox: [0, 0, 64, 48] },
      { class_name: 'person', confidence: 0.88, bbox: [320, 240, 640, 480] },
    ],
    ...overrides,
  };
}

describe('MissionCamera — media source abstraction', () => {
  it('renders image sources', () => {
    render(
      <CameraMedia
        source={{ kind: 'image', dataUri: 'data:image/jpeg;base64,Zm9v', alt: 'x' }}
      />
    );
    const img = screen.getByTestId('vision-image') as HTMLImageElement;
    expect(img.src).toBe('data:image/jpeg;base64,Zm9v');
  });

  it('reserves video and stream kinds for future phases', () => {
    const { rerender } = render(
      <CameraMedia source={{ kind: 'video', url: 'file.mp4' }} />
    );
    expect(screen.getByTestId('vision-unsupported-media')).toBeInTheDocument();
    rerender(<CameraMedia source={{ kind: 'stream', url: 'rtsp://x' }} />);
    expect(screen.getByTestId('vision-unsupported-media')).toBeInTheDocument();
  });
});

describe('MissionCamera — fallback', () => {
  it('shows "No camera inference available" when vision is null', () => {
    render(<MissionCamera vision={null} />);
    expect(
      screen.getByText('No camera inference available')
    ).toBeInTheDocument();
    expect(screen.getByText('NO FEED')).toBeInTheDocument();
    expect(screen.queryByTestId('vision-image')).not.toBeInTheDocument();
  });
});

describe('MissionCamera — image and detection overlay', () => {
  it('renders the analysed image from the base64 payload', () => {
    render(<MissionCamera vision={makeFrame()} />);
    const img = screen.getByTestId('vision-image') as HTMLImageElement;
    expect(img.src).toBe('data:image/jpeg;base64,Zm9vYmFy');
  });

  it('shows the LIVE indicator on the live feed', () => {
    render(<MissionCamera vision={makeFrame()} />);
    expect(screen.getByText('LIVE')).toBeInTheDocument();
  });

  it('renders one bounding box per detection', () => {
    render(<MissionCamera vision={makeFrame()} />);
    expect(screen.getAllByTestId('vision-bbox')).toHaveLength(3);
  });

  it('positions boxes as percentages of the original image size', () => {
    render(<MissionCamera vision={makeFrame()} />);
    const fireBox = screen.getAllByTestId('vision-bbox')[0];
    expect(fireBox.style.left).toBe('10%');    // 64 / 640
    expect(fireBox.style.top).toBe('10%');     // 48 / 480
    expect(fireBox.style.width).toBe('40%');   // (320-64) / 640
    expect(fireBox.style.height).toBe('40%');  // (240-48) / 480
  });

  it('uses the class color scheme: fire red, smoke orange, person blue', () => {
    expect(classColor('fire')).toBe('#ef4444');
    expect(classColor('smoke')).toBe('#f97316');
    expect(classColor('person')).toBe('#3b82f6');
    render(<MissionCamera vision={makeFrame()} />);
    const [fire, smoke, person] = screen.getAllByTestId('vision-bbox');
    expect(fire.style.borderColor).toBe('rgb(239, 68, 68)');
    expect(smoke.style.borderColor).toBe('rgb(249, 115, 22)');
    expect(person.style.borderColor).toBe('rgb(59, 130, 246)');
  });

  it('labels every box with class name and confidence', () => {
    render(<MissionCamera vision={makeFrame()} />);
    expect(screen.getByText('fire 94%')).toBeInTheDocument();
    expect(screen.getByText('smoke 81%')).toBeInTheDocument();
    expect(screen.getByText('person 88%')).toBeInTheDocument();
  });
});

describe('MissionCamera — telemetry bar', () => {
  it('shows detector, model, zone, frame, inference, threshold, resolution', () => {
    render(<MissionCamera vision={makeFrame()} />);
    const bar = screen.getByTestId('vision-status');
    expect(bar).toHaveTextContent('YOLO');
    expect(bar).toHaveTextContent('firerescue-detector-20260703.onnx');
    expect(bar).toHaveTextContent('2_3_1');
    expect(bar).toHaveTextContent('#7');
    expect(bar).toHaveTextContent('23.4 ms');
    expect(bar).toHaveTextContent('0.25');
    expect(bar).toHaveTextContent('640×480');
  });
});

describe('MissionCamera — history', () => {
  function renderFrames(count: number) {
    const first = makeFrame({ frame_id: 'f-0', frame_number: 0 });
    const view = render(<MissionCamera vision={first} />);
    for (let i = 1; i < count; i++) {
      view.rerender(
        <MissionCamera
          vision={makeFrame({
            frame_id: `f-${i}`,
            frame_number: i,
            zone_id: `${i}_0_1`,
          })}
        />
      );
    }
    return view;
  }

  it('accumulates analysed frames', () => {
    renderFrames(3);
    expect(screen.getAllByTestId('vision-history-item')).toHaveLength(3);
  });

  it('keeps only the last five frames', () => {
    renderFrames(8);
    expect(screen.getAllByTestId('vision-history-item')).toHaveLength(5);
  });

  it('clicking a history frame reviews it with timestamp and zone', () => {
    renderFrames(3);
    const items = screen.getAllByTestId('vision-history-item');
    fireEvent.click(items[items.length - 1]); // oldest (frame 0)
    expect(screen.getByTestId('vision-reviewing')).toHaveTextContent(
      'zone 2_3_1'
    );
    expect(screen.getByTestId('vision-status')).toHaveTextContent('#0');
  });

  it('the RETURN TO LIVE button restores the live feed', () => {
    renderFrames(3);
    fireEvent.click(screen.getAllByTestId('vision-history-item')[2]);
    expect(screen.getByTestId('vision-reviewing')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('vision-live-button'));
    expect(screen.queryByTestId('vision-reviewing')).not.toBeInTheDocument();
    expect(screen.getByTestId('vision-status')).toHaveTextContent('#2');
  });
});
