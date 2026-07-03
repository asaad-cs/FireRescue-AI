/**
 * TypeScript interfaces mirroring the backend Pydantic models exactly.
 * The frontend only ever receives MissionState from the WebSocket.
 * All types here map 1-to-1 to backend/models/mission_state.py and
 * backend/models/alert.py.
 *
 * datetime fields arrive as ISO 8601 strings after JSON serialization.
 */

// ─── Enums ────────────────────────────────────────────────────────────────────

export enum MissionStatus {
  IDLE = 'IDLE',
  INITIALIZING = 'INITIALIZING',
  ACTIVE = 'ACTIVE',
  PAUSED = 'PAUSED',
  ENDED = 'ENDED',
  CONNECTION_LOST = 'CONNECTION_LOST',
  ERROR = 'ERROR',
}

export enum HazardLevel {
  UNOBSERVED = 'UNOBSERVED',
  CLEAR = 'CLEAR',
  LOW = 'LOW',
  MODERATE = 'MODERATE',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL',
}

export enum AlertLevel {
  INFO = 'INFO',
  WARNING = 'WARNING',
  CRITICAL = 'CRITICAL',
  EMERGENCY = 'EMERGENCY',
}

export enum AlertType {
  HAZARD_ELEVATED = 'HAZARD_ELEVATED',
  VICTIM_DETECTED = 'VICTIM_DETECTED',
  SYSTEM = 'SYSTEM',
}

export enum ConnectionStatus {
  CONNECTED = 'CONNECTED',
  DISCONNECTED = 'DISCONNECTED',
  RECONNECTING = 'RECONNECTING',
}

// ─── Sub-models ───────────────────────────────────────────────────────────────

export interface DroneState {
  drone_id: string;
  x: number;
  y: number;
  floor: number;
  heading: number;
  last_seen: string | null; // ISO 8601 datetime
}

export interface ZoneState {
  zone_id: string;
  label: string;
  grid_x: number;
  grid_y: number;
  hazard_level: HazardLevel;
  victim_probability: number; // 0.0 – 1.0
  last_observed_at: string | null; // ISO 8601 datetime
}

export interface LatestReadings {
  temperature: number | null; // Celsius
  co_level: number | null;    // ppm
  smoke_density: number | null; // 0.0 – 1.0 normalized
}

export interface Alert {
  alert_id: string;
  mission_id: string;
  zone_id: string;
  alert_type: AlertType;
  level: AlertLevel;
  message: string;
  triggered_at: string; // ISO 8601 datetime
}

// ─── AI vision (Phase 8G) ─────────────────────────────────────────────────────

/** One object the vision detector found in the analysed image. */
export interface VisionDetection {
  class_name: string; // "fire" | "smoke" | "person"
  confidence: number; // 0.0 – 1.0
  bbox: number[];     // [x1, y1, x2, y2] in original image pixels
}

/**
 * What the AI vision detector saw and decided for the latest frame.
 * Null when the active detector performs no image inference
 * (GroundTruthDetector) or the frame carried no camera image.
 */
export interface VisionFrame {
  frame_id: string;
  zone_id: string;
  timestamp: string | null; // ISO 8601 datetime
  detector_name: string;
  model_name: string;
  frame_number: number;     // simulation tick
  image_base64: string;     // JPEG, base64-encoded
  image_width: number;
  image_height: number;
  inference_ms: number;
  confidence_threshold: number;
  detections: VisionDetection[];
}

// ─── Root model ───────────────────────────────────────────────────────────────

export interface MissionState {
  mission_id: string;
  status: MissionStatus;
  started_at: string | null;
  ended_at: string | null;
  elapsed_seconds: number;
  drone_state: DroneState | null;
  zone_states: Record<string, ZoneState>;
  active_alerts: Alert[];
  latest_readings: LatestReadings;
  alert_count: number;
  victim_signal_count: number;
  explored_percentage: number;
  connection_status: ConnectionStatus;
  vision?: VisionFrame | null; // Phase 8G — absent/null without image inference
}

// ─── Guards ───────────────────────────────────────────────────────────────────

/** Runtime check: is this object shaped like a MissionState from the backend? */
export function isMissionState(value: unknown): value is MissionState {
  if (typeof value !== 'object' || value === null) return false;
  const obj = value as Record<string, unknown>;
  return (
    typeof obj['mission_id'] === 'string' &&
    typeof obj['status'] === 'string' &&
    typeof obj['elapsed_seconds'] === 'number' &&
    typeof obj['zone_states'] === 'object' &&
    Array.isArray(obj['active_alerts'])
  );
}
