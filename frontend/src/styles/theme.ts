/**
 * Shared design tokens for the FireRescue AI dashboard.
 *
 * These constants complement the Tailwind configuration.
 * Use Tailwind classes where possible; reference these tokens when
 * dynamic class selection is required (e.g. hazard-level-specific styles).
 *
 * Dark theme is mandatory — the dashboard is used in low-light operational
 * environments where a light background causes glare and reduces contrast.
 */

import { HazardLevel, AlertLevel, MissionStatus } from '@/types/mission';

// ─── Hazard level styling ─────────────────────────────────────────────────────

export const HAZARD_BG: Record<HazardLevel, string> = {
  [HazardLevel.UNOBSERVED]: 'bg-hazard-unobserved',
  [HazardLevel.CLEAR]:      'bg-hazard-clear',
  [HazardLevel.LOW]:        'bg-hazard-low',
  [HazardLevel.MODERATE]:   'bg-hazard-moderate',
  [HazardLevel.HIGH]:       'bg-hazard-high',
  [HazardLevel.CRITICAL]:   'bg-hazard-critical',
};

export const HAZARD_TEXT: Record<HazardLevel, string> = {
  [HazardLevel.UNOBSERVED]: 'text-hazard-unobserved-text',
  [HazardLevel.CLEAR]:      'text-hazard-clear-text',
  [HazardLevel.LOW]:        'text-hazard-low-text',
  [HazardLevel.MODERATE]:   'text-hazard-moderate-text',
  [HazardLevel.HIGH]:       'text-hazard-high-text',
  [HazardLevel.CRITICAL]:   'text-hazard-critical-text',
};

export const HAZARD_BORDER: Record<HazardLevel, string> = {
  [HazardLevel.UNOBSERVED]: 'border-border-subtle',
  [HazardLevel.CLEAR]:      'border-hazard-clear-text/30',
  [HazardLevel.LOW]:        'border-hazard-low-text/30',
  [HazardLevel.MODERATE]:   'border-hazard-moderate-text/40',
  [HazardLevel.HIGH]:       'border-hazard-high-text/50',
  [HazardLevel.CRITICAL]:   'border-hazard-critical-text/60',
};

export const HAZARD_LABEL: Record<HazardLevel, string> = {
  [HazardLevel.UNOBSERVED]: 'UNOBSERVED',
  [HazardLevel.CLEAR]:      'CLEAR',
  [HazardLevel.LOW]:        'LOW',
  [HazardLevel.MODERATE]:   'MODERATE',
  [HazardLevel.HIGH]:       'HIGH',
  [HazardLevel.CRITICAL]:   'CRITICAL',
};

// ─── Alert level styling ──────────────────────────────────────────────────────

export const ALERT_BG: Record<AlertLevel, string> = {
  [AlertLevel.INFO]:      'bg-alert-info-bg',
  [AlertLevel.WARNING]:   'bg-alert-warning-bg',
  [AlertLevel.CRITICAL]:  'bg-alert-critical-bg',
  [AlertLevel.EMERGENCY]: 'bg-alert-emergency-bg',
};

export const ALERT_BORDER: Record<AlertLevel, string> = {
  [AlertLevel.INFO]:      'border-alert-info-border',
  [AlertLevel.WARNING]:   'border-alert-warning-border',
  [AlertLevel.CRITICAL]:  'border-alert-critical-border',
  [AlertLevel.EMERGENCY]: 'border-alert-emergency-border',
};

export const ALERT_TEXT: Record<AlertLevel, string> = {
  [AlertLevel.INFO]:      'text-alert-info-text',
  [AlertLevel.WARNING]:   'text-alert-warning-text',
  [AlertLevel.CRITICAL]:  'text-alert-critical-text',
  [AlertLevel.EMERGENCY]: 'text-alert-emergency-text',
};

// ─── Mission status styling ───────────────────────────────────────────────────

export const STATUS_DOT: Record<MissionStatus, string> = {
  [MissionStatus.IDLE]:             'bg-status-idle',
  [MissionStatus.INITIALIZING]:     'bg-status-connecting',
  [MissionStatus.ACTIVE]:           'bg-status-active',
  [MissionStatus.PAUSED]:           'bg-status-paused',
  [MissionStatus.ENDED]:            'bg-status-ended',
  [MissionStatus.CONNECTION_LOST]:  'bg-status-lost',
  [MissionStatus.ERROR]:            'bg-status-error',
};

export const STATUS_LABEL: Record<MissionStatus, string> = {
  [MissionStatus.IDLE]:             'IDLE',
  [MissionStatus.INITIALIZING]:     'INITIALIZING',
  [MissionStatus.ACTIVE]:           'MISSION ACTIVE',
  [MissionStatus.PAUSED]:           'PAUSED',
  [MissionStatus.ENDED]:            'MISSION ENDED',
  [MissionStatus.CONNECTION_LOST]:  'CONNECTION LOST',
  [MissionStatus.ERROR]:            'SYSTEM ERROR',
};

// ─── Layout constants ─────────────────────────────────────────────────────────

export const LAYOUT = {
  topNavHeight: '3rem',       // 48px
  rightSidebarWidth: '22rem', // 352px
  bottomTimelineHeight: '6rem', // 96px
} as const;
