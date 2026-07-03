/**
 * MissionCamera — the primary visual element of the operations center:
 * what the drone's camera sees and what the AI decided about it.
 *
 * Media abstraction (future-proof by design): the display stage renders
 * a CameraMediaSource. Today the simulation produces still images
 * (kind "image"); video files, live streams, and drone feeds later
 * only need a new source kind handled inside CameraMedia — the layout,
 * overlay, telemetry bar, and history rail stay untouched.
 *
 * Shows:
 *   - the exact analysed frame (never reloaded from disk, never
 *     re-inferred) on a video-ready 16:9 dark stage
 *   - professional detection overlay: class-colored boxes with
 *     label + confidence pills (fire red / smoke orange / person blue)
 *   - telemetry bar: detector, model, zone, frame #, inference time,
 *     confidence threshold, resolution
 *   - the last five analysed frames; click to review, LIVE to return
 *   - a "No camera inference available" stage when the active detector
 *     performs no image analysis (GroundTruthDetector)
 */

import { useEffect, useState } from 'react';
import { type VisionFrame } from '@/types/mission';
import { formatTimestamp } from '@/utils/format';

const HISTORY_LIMIT = 5;

const CLASS_COLORS: Record<string, string> = {
  fire:   '#ef4444', // red
  smoke:  '#f97316', // orange
  person: '#3b82f6', // blue
};
const FALLBACK_COLOR = '#94a3b8';

export function classColor(className: string): string {
  return CLASS_COLORS[className] ?? FALLBACK_COLOR;
}

// ── Media source abstraction ──────────────────────────────────────────────────

/** Everything the camera stage can display, today and in future phases. */
export type CameraMediaSource =
  | { kind: 'image'; dataUri: string; alt: string }
  | { kind: 'video'; url: string }    // future: recorded video files
  | { kind: 'stream'; url: string };  // future: live drone / RTSP feeds

/** Renders one media source. New source kinds are added ONLY here. */
export function CameraMedia({ source }: { source: CameraMediaSource }) {
  switch (source.kind) {
    case 'image':
      return (
        <img
          data-testid="vision-image"
          src={source.dataUri}
          alt={source.alt}
          className="h-full w-full object-contain"
        />
      );
    case 'video':
    case 'stream':
      // Reserved for future phases — the stage and overlay are already
      // media-agnostic; only this switch needs the new player.
      return (
        <div
          data-testid="vision-unsupported-media"
          className="flex h-full w-full items-center justify-center font-mono text-2xs text-text-muted"
        >
          {source.kind} sources arrive in a future phase
        </div>
      );
  }
}

// ── Detection overlay ─────────────────────────────────────────────────────────

function BoundingBoxes({ frame }: { frame: VisionFrame }) {
  const { image_width: w, image_height: h } = frame;
  if (!w || !h) return null;
  return (
    <>
      {frame.detections.map((det, i) => {
        const [x1, y1, x2, y2] = det.bbox;
        const color = classColor(det.class_name);
        return (
          <div
            key={`${frame.frame_id}-${i}`}
            data-testid="vision-bbox"
            className="absolute rounded-sm border-2"
            style={{
              left:   `${(x1 / w) * 100}%`,
              top:    `${(y1 / h) * 100}%`,
              width:  `${((x2 - x1) / w) * 100}%`,
              height: `${((y2 - y1) / h) * 100}%`,
              borderColor: color,
              boxShadow: `0 0 0 1px #000a, inset 0 0 12px ${color}22`,
            }}
          >
            <span
              className="absolute left-0 top-0 -translate-y-full whitespace-nowrap rounded-t px-1.5 py-0.5 font-mono text-2xs font-bold uppercase tracking-wide text-white"
              style={{ backgroundColor: color, textShadow: '0 1px 2px #000c' }}
            >
              {det.class_name} {Math.round(det.confidence * 100)}%
            </span>
          </div>
        );
      })}
    </>
  );
}

// ── Telemetry bar ─────────────────────────────────────────────────────────────

function TelemetryField({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-w-0 flex-col">
      <span className="font-mono text-[0.5rem] uppercase tracking-widest text-text-muted">
        {label}
      </span>
      <span className="truncate font-mono text-2xs font-semibold text-text-primary" title={value}>
        {value}
      </span>
    </div>
  );
}

function TelemetryBar({ frame }: { frame: VisionFrame }) {
  return (
    <div
      data-testid="vision-status"
      className="grid shrink-0 grid-cols-7 gap-3 border-t border-border-subtle px-3 py-1.5"
    >
      <TelemetryField label="Detector"   value={frame.detector_name.toUpperCase()} />
      <TelemetryField label="Model"      value={frame.model_name} />
      <TelemetryField label="Zone"       value={frame.zone_id} />
      <TelemetryField label="Frame"      value={`#${frame.frame_number}`} />
      <TelemetryField label="Inference"  value={`${frame.inference_ms.toFixed(1)} ms`} />
      <TelemetryField label="Conf. threshold" value={frame.confidence_threshold.toFixed(2)} />
      <TelemetryField label="Resolution" value={`${frame.image_width}×${frame.image_height}`} />
    </div>
  );
}

// ── Camera panel ──────────────────────────────────────────────────────────────

interface MissionCameraProps {
  vision: VisionFrame | null;
}

export function MissionCamera({ vision }: MissionCameraProps) {
  const [history, setHistory] = useState<VisionFrame[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Record each newly analysed frame (newest first, capped).
  useEffect(() => {
    if (!vision) return;
    setHistory((prev) => {
      if (prev[0]?.frame_id === vision.frame_id) return prev;
      return [vision, ...prev.filter((f) => f.frame_id !== vision.frame_id)]
        .slice(0, HISTORY_LIMIT);
    });
  }, [vision]);

  const selected = selectedId
    ? history.find((f) => f.frame_id === selectedId) ?? null
    : null;
  const displayed = selected ?? vision;

  return (
    <div
      data-testid="mission-camera"
      className="flex h-full flex-col overflow-hidden rounded-lg border border-border-default bg-bg-surface"
    >
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-border-subtle px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold tracking-wider text-text-primary">
            MISSION CAMERA
          </span>
          <span className="font-mono text-[0.5rem] uppercase tracking-widest text-text-muted">
            drone feed · SIM-CAM-01
          </span>
        </div>
        {selected ? (
          <button
            data-testid="vision-live-button"
            onClick={() => setSelectedId(null)}
            className="flex items-center gap-1.5 rounded px-2.5 py-1 font-mono text-2xs font-bold text-white transition-colors"
            style={{ backgroundColor: '#1e4d7a' }}
          >
            ⏵ RETURN TO LIVE
          </button>
        ) : (
          <span className="flex items-center gap-1.5 font-mono text-2xs font-semibold">
            {displayed ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60" style={{ backgroundColor: '#ef4444' }} />
                  <span className="relative inline-flex h-2 w-2 rounded-full" style={{ backgroundColor: '#ef4444' }} />
                </span>
                <span style={{ color: '#ef4444' }}>LIVE</span>
              </>
            ) : (
              <span className="text-text-muted">NO FEED</span>
            )}
          </span>
        )}
      </div>

      {!displayed ? (
        /* GroundTruthDetector active, or no image on the frame */
        <div className="flex flex-1 flex-col items-center justify-center gap-2 bg-black/40 p-4">
          <span aria-hidden="true" className="text-2xl opacity-30">📷</span>
          <span className="text-center font-mono text-xs text-text-muted">
            No camera inference available
          </span>
          <span className="text-center font-mono text-2xs text-text-dim">
            (active detector performs no image analysis)
          </span>
        </div>
      ) : (
        <>
          <div className="flex min-h-0 flex-1">
            {/* Video-ready media stage */}
            <div className="relative flex min-w-0 flex-1 items-center justify-center overflow-hidden bg-black">
              <div
                data-testid="vision-image-container"
                className="relative max-h-full max-w-full"
                style={{
                  aspectRatio: `${displayed.image_width || 1} / ${displayed.image_height || 1}`,
                  height: '100%',
                }}
              >
                <CameraMedia
                  source={{
                    kind: 'image',
                    dataUri: `data:image/jpeg;base64,${displayed.image_base64}`,
                    alt: `Camera frame ${displayed.frame_number}, zone ${displayed.zone_id}`,
                  }}
                />
                <BoundingBoxes frame={displayed} />
              </div>
              {selected && (
                <span
                  data-testid="vision-reviewing"
                  className="absolute left-2 top-2 rounded px-2 py-1 font-mono text-2xs font-bold"
                  style={{ backgroundColor: '#1e1200ee', color: '#fbbf24' }}
                >
                  REVIEWING {formatTimestamp(selected.timestamp ?? '')} · zone{' '}
                  {selected.zone_id}
                </span>
              )}
            </div>

            {/* History rail — last five analysed frames */}
            <div className="flex w-24 shrink-0 flex-col gap-1.5 overflow-y-auto border-l border-border-subtle p-1.5">
              <span className="font-mono text-[0.5rem] uppercase tracking-widest text-text-muted">
                History
              </span>
              {history.map((frame) => (
                <button
                  key={frame.frame_id}
                  data-testid="vision-history-item"
                  onClick={() => setSelectedId(frame.frame_id)}
                  className="rounded border transition-transform hover:scale-[1.03]"
                  style={{
                    borderColor:
                      frame.frame_id === (selected ?? vision)?.frame_id
                        ? '#38bdf8'
                        : '#1a2435',
                  }}
                  title={`Frame #${frame.frame_number} — zone ${frame.zone_id}`}
                >
                  <img
                    src={`data:image/jpeg;base64,${frame.image_base64}`}
                    alt={`History frame ${frame.frame_number}`}
                    className="w-full rounded-t object-cover"
                  />
                  <span className="block truncate px-1 font-mono text-[0.5rem] text-text-muted">
                    #{frame.frame_number} {frame.zone_id}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <TelemetryBar frame={displayed} />
        </>
      )}
    </div>
  );
}
