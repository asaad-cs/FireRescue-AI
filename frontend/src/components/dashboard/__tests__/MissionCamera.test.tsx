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

// ── Phase 8K — live camera monitor ────────────────────────────────────────────

describe('MissionCamera — link states (Phase 8K)', () => {
  it('shows ACQUIRING SIGNAL when the link is down and no frame exists', () => {
    render(<MissionCamera vision={null} wsStatus="reconnecting" />);
    expect(screen.getByTestId('vision-signal-lost')).toBeInTheDocument();
    expect(screen.getByText('ACQUIRING SIGNAL')).toBeInTheDocument();
    expect(screen.getByText('SIGNAL LOST')).toBeInTheDocument();
    expect(
      screen.queryByText('No camera inference available')
    ).not.toBeInTheDocument();
  });

  it('marks a frozen frame as STALE when the link drops mid-mission', () => {
    render(
      <MissionCamera vision={makeFrame()} wsStatus="reconnecting" isStale />
    );
    expect(screen.getByTestId('vision-stale')).toBeInTheDocument();
    // Header indicator and the telemetry Link field both read STALE.
    expect(screen.getAllByText('STALE').length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByText('LIVE')).not.toBeInTheDocument();
    expect(screen.getByTestId('vision-status')).toHaveTextContent('STALE');
  });

  it('stays fully backward compatible with vision-only usage', () => {
    render(<MissionCamera vision={makeFrame()} />);
    expect(screen.getByText('LIVE')).toBeInTheDocument();
    expect(screen.queryByTestId('vision-stale')).not.toBeInTheDocument();
  });
});

describe('MissionCamera — HUD and metadata (Phase 8K)', () => {
  it('renders the stage HUD with zone, clock, frame and feed identity', () => {
    render(<MissionCamera vision={makeFrame()} />);
    const hud = screen.getByTestId('camera-hud');
    expect(hud).toHaveTextContent('ZONE 2_3_1');
    expect(hud).toHaveTextContent('FRAME #7');
    expect(hud).toHaveTextContent('SIM-CAM-01 · SIMULATED FEED');
  });

  it('shows a contact counter chip reflecting the detections', () => {
    render(<MissionCamera vision={makeFrame()} />);
    expect(screen.getByTestId('vision-contacts')).toHaveTextContent(
      '3 CONTACTS'
    );
  });

  it('shows NO CONTACTS when the frame has no detections', () => {
    render(<MissionCamera vision={makeFrame({ detections: [] })} />);
    expect(screen.getByTestId('vision-contacts')).toHaveTextContent(
      'NO CONTACTS'
    );
  });

  it('extends telemetry with target count and link mode', () => {
    render(<MissionCamera vision={makeFrame()} />);
    const bar = screen.getByTestId('vision-status');
    expect(bar).toHaveTextContent('Targets');
    expect(bar).toHaveTextContent('3');
    expect(bar).toHaveTextContent('SIMULATED');
  });
});

describe('MissionCamera — mission-scoped history (Phase 8K fixes)', () => {
  it('clears the history rail when a new mission starts', () => {
    const view = render(
      <MissionCamera vision={makeFrame({ frame_id: 'a-1' })} missionId="m-1" />
    );
    view.rerender(
      <MissionCamera
        vision={makeFrame({ frame_id: 'a-2', frame_number: 8 })}
        missionId="m-1"
      />
    );
    expect(screen.getAllByTestId('vision-history-item')).toHaveLength(2);
    // Backend restarts → new mission_id → the rail must start empty and
    // then hold ONLY the new mission's first frame.
    view.rerender(
      <MissionCamera
        vision={makeFrame({ frame_id: 'b-1', frame_number: 0, zone_id: '0_0_1' })}
        missionId="m-2"
      />
    );
    const items = screen.getAllByTestId('vision-history-item');
    expect(items).toHaveLength(1);
    expect(items[0]).toHaveTextContent('#0 0_0_1');
  });

  it('exits a history review when a new mission starts', () => {
    const view = render(
      <MissionCamera vision={makeFrame({ frame_id: 'a-1' })} missionId="m-1" />
    );
    fireEvent.click(screen.getByTestId('vision-history-item'));
    expect(screen.getByTestId('vision-reviewing')).toBeInTheDocument();
    view.rerender(
      <MissionCamera
        vision={makeFrame({ frame_id: 'b-1' })}
        missionId="m-2"
      />
    );
    expect(screen.queryByTestId('vision-reviewing')).not.toBeInTheDocument();
  });
});

describe('MissionCamera — replay awareness (Phase 8K fixes)', () => {
  it('shows REPLAY instead of LIVE while replaying', () => {
    render(<MissionCamera vision={makeFrame()} isReplaying />);
    expect(screen.getByTestId('vision-replay-indicator')).toHaveTextContent(
      'REPLAY'
    );
    expect(screen.queryByText('LIVE')).not.toBeInTheDocument();
  });

  it('does not record replayed frames into the history rail', () => {
    const view = render(
      <MissionCamera vision={makeFrame({ frame_id: 'live-1' })} missionId="m-1" />
    );
    view.rerender(
      <MissionCamera
        vision={makeFrame({ frame_id: 'replayed-0', frame_number: 0 })}
        missionId="m-1"
        isReplaying
      />
    );
    // Still only the live frame — the replayed frame displays but is
    // not recorded.
    const items = screen.getAllByTestId('vision-history-item');
    expect(items).toHaveLength(1);
    expect(items[0]).toHaveTextContent('#7');
    expect(screen.getByTestId('vision-status')).toHaveTextContent('#0');
  });

  it('keeps LIVE behavior unchanged when not replaying', () => {
    render(<MissionCamera vision={makeFrame()} />);
    expect(screen.getByText('LIVE')).toBeInTheDocument();
    expect(
      screen.queryByTestId('vision-replay-indicator')
    ).not.toBeInTheDocument();
  });
});

describe('MissionCamera — HUD bands never overlap labels (Phase 8K fixes)', () => {
  it('renders HUD text in bands outside the image container', () => {
    render(<MissionCamera vision={makeFrame()} />);
    const container = screen.getByTestId('vision-image-container');
    const hud = screen.getByTestId('camera-hud');
    // Zone/clock/frame chips are HUD-band children, never descendants
    // of the image container that hosts the detection boxes.
    for (const text of ['ZONE 2_3_1', 'FRAME #7', 'SIM-CAM-01 · SIMULATED FEED']) {
      const el = Array.from(hud.querySelectorAll('span')).find((s) =>
        (s.textContent ?? '').trim().startsWith(text.split(' ')[0])
      );
      expect(el).toBeTruthy();
    }
    expect(container.textContent).not.toContain('ZONE ');
    expect(container.textContent).not.toContain('FRAME #');
    expect(container.textContent).not.toContain('SIMULATED FEED');
  });
});

describe('MissionCamera — edge-aware detection labels (Phase 8K)', () => {
  it('flips the label inside the box when it touches the top edge', () => {
    render(<MissionCamera vision={makeFrame()} />);
    const labels = screen.getAllByTestId('vision-bbox-label');
    // fire bbox starts at y=48 (10% of 480) → label above the box
    expect(labels[0].className).toContain('-translate-y-full');
    // smoke bbox starts at y=0 → label rendered inside the box
    expect(labels[1].className).not.toContain('-translate-y-full');
  });

  it('right-aligns the label when the box hugs the right edge', () => {
    render(<MissionCamera vision={makeFrame()} />);
    const labels = screen.getAllByTestId('vision-bbox-label');
    // person bbox starts at x=320 (50% of 640) → left-anchored
    expect(labels[2].className).toContain('left-0');
    const wide = makeFrame({
      detections: [
        { class_name: 'fire', confidence: 0.9, bbox: [512, 240, 640, 480] },
      ],
    });
    render(<MissionCamera vision={wide} />);
    const edgeLabel = screen.getAllByTestId('vision-bbox-label').pop()!;
    // x1=512 (80% of 640) → right-anchored so the pill never clips
    expect(edgeLabel.className).toContain('right-0');
  });
});
