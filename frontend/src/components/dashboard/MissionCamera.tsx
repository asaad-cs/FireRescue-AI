/**
 * MissionCamera — the primary visual element of the operations center:
 * a live camera monitor showing what the drone sees and what the AI
 * decided about it (Phase 8I.1, redesigned as a monitor in Phase 8K).
 *
 * Media abstraction (future-proof by design): the display stage renders
 * a CameraMediaSource. Today the simulation produces still images
 * (kind "image"); video files, live streams, and drone feeds later
 * only need a new source kind handled inside CameraMedia — the stage,
 * HUD, overlay, telemetry bar, and history rail stay untouched.
 *
 * Monitor design (Phase 8K):
 *   - HUD bands above and below the media viewport: zone + UTC clock,
 *     frame counter, feed identity. The bands are OUTSIDE the image
 *     area by construction, so HUD text and detection labels can
 *     never overlap, whatever the box geometry.
 *   - detection overlay with edge-aware labels: class-colored boxes
 *     whose label pills flip inside the frame near the top edge and
 *     right-align near the right edge (never clipped)
 *   - link/mode awareness: LIVE / REPLAY / STALE / SIGNAL LOST /
 *     NO FEED, driven by state the layout already tracks
 *   - history is mission-scoped: it resets when a new mission starts
 *     and is frozen (not recorded) while a replay is running
 *   - telemetry bar: detector, model, zone, frame #, inference time,
 *     confidence threshold, resolution, targets, link
 *   - the last five analysed frames; click to review, LIVE to return
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
const HUD_COLOR = '#38bdf8';
const HUD_BAND_BG = '#05080d';

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
        // Edge-aware label placement: flip inside the box near the top
        // edge, right-align near the right edge — never clip the pill.
        const nearTop = y1 / h < 0.08;
        const nearRight = x1 / w > 0.7;
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
              data-testid="vision-bbox-label"
              className={[
                'absolute whitespace-nowrap px-1.5 py-0.5 font-mono text-2xs font-bold uppercase tracking-wide text-white',
                nearTop ? 'top-0 rounded-b' : 'top-0 -translate-y-full rounded-t',
                nearRight ? 'right-0' : 'left-0',
              ].join(' ')}
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

// ── Stage chrome (camera-monitor look) ────────────────────────────────────────

function CornerBrackets() {
  const seg = 'absolute h-4 w-4';
  const b = `2px solid ${HUD_COLOR}66`;
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-1">
      <span className={`${seg} left-0 top-0`}     style={{ borderLeft: b, borderTop: b }} />
      <span className={`${seg} right-0 top-0`}    style={{ borderRight: b, borderTop: b }} />
      <span className={`${seg} bottom-0 left-0`}  style={{ borderLeft: b, borderBottom: b }} />
      <span className={`${seg} bottom-0 right-0`} style={{ borderRight: b, borderBottom: b }} />
    </div>
  );
}

/** Scanlines + vignette that make the stage read as a monitor, not an <img>. */
function MonitorTexture() {
  return (
    <>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage:
            'repeating-linear-gradient(0deg, transparent 0px, transparent 2px, #000 3px, #000 4px)',
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse at center, transparent 64%, rgba(0,0,0,0.5) 100%)',
        }}
      />
    </>
  );
}

const HUD_TEXT = 'whitespace-nowrap font-mono text-2xs font-semibold';

/** Slim strip above the media viewport: zone, clock, status chip, frame #. */
function HudTopBand({
  frame,
  reviewing,
  isStale,
}: {
  frame: VisionFrame;
  reviewing: VisionFrame | null;
  isStale: boolean;
}) {
  return (
    <div
      className="flex h-7 shrink-0 items-center justify-between gap-3 border-b border-border-subtle px-2"
      style={{ backgroundColor: HUD_BAND_BG }}
    >
      <div className="flex min-w-0 items-center gap-2">
        <span className={HUD_TEXT} style={{ color: HUD_COLOR }}>
          ZONE {frame.zone_id}
        </span>
        <span className={`${HUD_TEXT} text-text-muted`}>
          {formatTimestamp(frame.timestamp ?? '')} UTC
        </span>
      </div>
      {reviewing ? (
        <span
          data-testid="vision-reviewing"
          className={`${HUD_TEXT} truncate rounded px-2`}
          style={{ backgroundColor: '#1e1200', color: '#fbbf24' }}
        >
          REVIEWING {formatTimestamp(reviewing.timestamp ?? '')} · zone{' '}
          {reviewing.zone_id}
        </span>
      ) : isStale ? (
        <span
          data-testid="vision-stale"
          className={`${HUD_TEXT} truncate rounded px-2`}
          style={{ backgroundColor: '#1e1200', color: '#f59e0b' }}
        >
          FEED STALE — link down, showing last frame #{frame.frame_number}
        </span>
      ) : null}
      <span className={`${HUD_TEXT} text-text-muted`}>
        FRAME #{frame.frame_number}
      </span>
    </div>
  );
}

/** Slim strip below the media viewport: feed identity. */
function HudBottomBand() {
  return (
    <div
      className="flex h-7 shrink-0 items-center border-t border-border-subtle px-2"
      style={{ backgroundColor: HUD_BAND_BG }}
    >
      <span className={`${HUD_TEXT} text-text-muted`}>
        SIM-CAM-01 · SIMULATED FEED
      </span>
    </div>
  );
}

// ── Telemetry bar ─────────────────────────────────────────────────────────────

function TelemetryField({ label, value, valueColor }: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <div className="flex min-w-0 flex-col">
      <span className="font-mono text-[0.5rem] uppercase tracking-widest text-text-muted">
        {label}
      </span>
      <span
        className="truncate font-mono text-2xs font-semibold text-text-primary"
        style={valueColor ? { color: valueColor } : undefined}
        title={value}
      >
        {value}
      </span>
    </div>
  );
}

function TelemetryBar({ frame, isStale }: { frame: VisionFrame; isStale: boolean }) {
  return (
    <div
      data-testid="vision-status"
      className="grid shrink-0 grid-cols-9 gap-3 border-t border-border-subtle px-3 py-1.5"
    >
      <TelemetryField label="Detector"   value={frame.detector_name.toUpperCase()} />
      <TelemetryField label="Model"      value={frame.model_name} />
      <TelemetryField label="Zone"       value={frame.zone_id} />
      <TelemetryField label="Frame"      value={`#${frame.frame_number}`} />
      <TelemetryField label="Inference"  value={`${frame.inference_ms.toFixed(1)} ms`} />
      <TelemetryField label="Conf. threshold" value={frame.confidence_threshold.toFixed(2)} />
      <TelemetryField label="Resolution" value={`${frame.image_width}×${frame.image_height}`} />
      <TelemetryField
        label="Targets"
        value={String(frame.detections.length)}
        valueColor={frame.detections.length > 0 ? '#f87171' : undefined}
      />
      <TelemetryField
        label="Link"
        value={isStale ? 'STALE' : 'SIMULATED'}
        valueColor={isStale ? '#f59e0b' : undefined}
      />
    </div>
  );
}

// ── Empty states ──────────────────────────────────────────────────────────────

/** The WebSocket link is down and no frame was ever received. */
function SignalLostStage() {
  return (
    <div
      data-testid="vision-signal-lost"
      className="flex flex-1 flex-col items-center justify-center gap-2 bg-black/40 p-4"
    >
      <span aria-hidden="true" className="animate-reconnect-blink text-2xl opacity-40">📡</span>
      <span className="text-center font-mono text-xs font-semibold" style={{ color: '#f59e0b' }}>
        ACQUIRING SIGNAL
      </span>
      <span className="text-center font-mono text-2xs text-text-dim">
        telemetry link down — reconnecting to mission feed
      </span>
    </div>
  );
}

/** Connected, but the active detector performs no image analysis. */
function NoInferenceStage() {
  return (
    <div className="relative flex flex-1 flex-col items-center justify-center gap-2 bg-black/40 p-4">
      <MonitorTexture />
      <CornerBrackets />
      <span aria-hidden="true" className="text-2xl opacity-30">📷</span>
      <span className="text-center font-mono text-xs text-text-muted">
        No camera inference available
      </span>
      <span className="text-center font-mono text-2xs text-text-dim">
        (active detector performs no image analysis)
      </span>
      <span className="mt-1 rounded border border-border-subtle px-2 py-0.5 font-mono text-[0.5rem] uppercase tracking-widest text-text-dim">
        Standby · SIM-CAM-01
      </span>
    </div>
  );
}

// ── Camera panel ──────────────────────────────────────────────────────────────

interface MissionCameraProps {
  vision: VisionFrame | null;
  /** Active mission id; a change resets the mission-scoped history. */
  missionId?: string | null;
  /** WebSocket status from the layout; anything but 'connected' = link down. */
  wsStatus?: string;
  /** True when the link dropped mid-mission — the shown frame is frozen. */
  isStale?: boolean;
  /** True while the operator replays the recorded mission. */
  isReplaying?: boolean;
}

export function MissionCamera({
  vision,
  missionId = null,
  wsStatus = 'connected',
  isStale = false,
  isReplaying = false,
}: MissionCameraProps) {
  const [history, setHistory] = useState<VisionFrame[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // History is mission-scoped: a new mission id clears it (declared
  // before the recording effect so a new mission's first frame lands
  // in an already-empty rail).
  useEffect(() => {
    setHistory([]);
    setSelectedId(null);
  }, [missionId]);

  // Record each newly analysed frame (newest first, capped). Replayed
  // frames are displayed but never recorded — the rail keeps the live
  // mission's history while the operator scrubs the past.
  useEffect(() => {
    if (!vision || isReplaying) return;
    setHistory((prev) => {
      if (prev[0]?.frame_id === vision.frame_id) return prev;
      return [vision, ...prev.filter((f) => f.frame_id !== vision.frame_id)]
        .slice(0, HISTORY_LIMIT);
    });
  }, [vision, isReplaying]);

  const selected = selectedId
    ? history.find((f) => f.frame_id === selectedId) ?? null
    : null;
  const displayed = selected ?? vision;
  const linkDown = wsStatus !== 'connected';

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
          {displayed && (
            <span
              data-testid="vision-contacts"
              className="rounded px-1.5 py-0.5 font-mono text-[0.55rem] font-bold tracking-widest"
              style={
                displayed.detections.length > 0
                  ? { color: '#f87171', backgroundColor: '#f871711a', border: '1px solid #f8717155' }
                  : { color: '#22c55e', backgroundColor: '#22c55e14', border: '1px solid #22c55e44' }
              }
            >
              {displayed.detections.length > 0
                ? `${displayed.detections.length} CONTACT${displayed.detections.length > 1 ? 'S' : ''}`
                : 'NO CONTACTS'}
            </span>
          )}
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
            {displayed && isReplaying ? (
              <span
                data-testid="vision-replay-indicator"
                className="flex items-center gap-1.5"
                style={{ color: HUD_COLOR }}
              >
                <span className="relative inline-flex h-2 w-2 rounded-full" style={{ backgroundColor: HUD_COLOR }} />
                REPLAY
              </span>
            ) : displayed && isStale ? (
              <>
                <span className="animate-reconnect-blink relative inline-flex h-2 w-2 rounded-full" style={{ backgroundColor: '#f59e0b' }} />
                <span style={{ color: '#f59e0b' }}>STALE</span>
              </>
            ) : displayed ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60" style={{ backgroundColor: '#ef4444' }} />
                  <span className="relative inline-flex h-2 w-2 rounded-full" style={{ backgroundColor: '#ef4444' }} />
                </span>
                <span style={{ color: '#ef4444' }}>LIVE</span>
              </>
            ) : linkDown ? (
              <span className="animate-reconnect-blink" style={{ color: '#ef4444' }}>
                SIGNAL LOST
              </span>
            ) : (
              <span className="text-text-muted">NO FEED</span>
            )}
          </span>
        )}
      </div>

      {!displayed ? (
        linkDown ? (
          <SignalLostStage />
        ) : (
          <NoInferenceStage />
        )
      ) : (
        <>
          <div className="flex min-h-0 flex-1">
            {/* Video-ready media stage: HUD bands frame the viewport, so
                HUD text lives outside the image and can never collide
                with detection labels. */}
            <div
              data-testid="camera-hud"
              className="flex min-w-0 flex-1 flex-col overflow-hidden bg-black"
            >
              <HudTopBand
                frame={displayed}
                reviewing={selected}
                isStale={!selected && isStale}
              />
              <div className="relative flex min-h-0 flex-1 items-center justify-center p-2.5">
                <div
                  key={displayed.frame_id}
                  data-testid="vision-image-container"
                  className="animate-camera-frame-in relative max-h-full max-w-full"
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
                <MonitorTexture />
                <CornerBrackets />
              </div>
              <HudBottomBand />
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
                  title={`Frame #${frame.frame_number} — zone ${frame.zone_id}${
                    frame.detections.length
                      ? ` — ${frame.detections.length} detection(s)`
                      : ''
                  }`}
                >
                  <img
                    src={`data:image/jpeg;base64,${frame.image_base64}`}
                    alt={`History frame ${frame.frame_number}`}
                    className="w-full rounded-t object-cover"
                  />
                  <span className="flex items-center gap-1 px-1">
                    {[...new Set(frame.detections.map((d) => d.class_name))].map(
                      (cls) => (
                        <span
                          key={cls}
                          aria-hidden="true"
                          className="h-1.5 w-1.5 shrink-0 rounded-full"
                          style={{ backgroundColor: classColor(cls) }}
                        />
                      )
                    )}
                    <span className="block truncate font-mono text-[0.5rem] text-text-muted">
                      #{frame.frame_number} {frame.zone_id}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          </div>

          <TelemetryBar frame={displayed} isStale={isStale} />
        </>
      )}
    </div>
  );
}
