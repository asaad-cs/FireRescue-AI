import { describe, it, expect } from 'vitest';
import {
  formatElapsed,
  formatTimestamp,
  formatRelative,
  formatPct,
  formatMissionId,
  formatProbability,
  formatTemperature,
  formatCoLevel,
  formatSmokeDensity,
} from '@/utils/format';

describe('formatElapsed', () => {
  it('formats zero seconds', () => {
    expect(formatElapsed(0)).toBe('00:00:00');
  });

  it('formats seconds only', () => {
    expect(formatElapsed(45)).toBe('00:00:45');
  });

  it('formats minutes and seconds', () => {
    expect(formatElapsed(125)).toBe('00:02:05');
  });

  it('formats hours, minutes, seconds', () => {
    expect(formatElapsed(3723)).toBe('01:02:03');
  });

  it('clamps negative input to zero', () => {
    expect(formatElapsed(-10)).toBe('00:00:00');
  });

  it('pads single digits with leading zero', () => {
    expect(formatElapsed(65)).toBe('00:01:05');
  });
});

describe('formatTimestamp', () => {
  it('returns a formatted time string for a valid ISO string', () => {
    const result = formatTimestamp('2026-07-01T14:30:45Z');
    // Time will be locale-specific but should be a time string
    expect(result).toMatch(/\d{2}:\d{2}:\d{2}/);
  });

  it('returns fallback for invalid input', () => {
    expect(formatTimestamp('not-a-date')).toBe('--:--:--');
  });
});

describe('formatRelative', () => {
  it('returns "just now" for very recent timestamps', () => {
    const now = new Date().toISOString();
    expect(formatRelative(now)).toBe('just now');
  });

  it('returns seconds ago for timestamps < 60s', () => {
    const past = new Date(Date.now() - 30_000).toISOString();
    expect(formatRelative(past)).toMatch(/30s ago/);
  });

  it('returns minutes ago for timestamps < 1h', () => {
    const past = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    expect(formatRelative(past)).toMatch(/5m ago/);
  });

  it('returns hours ago for older timestamps', () => {
    const past = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    expect(formatRelative(past)).toMatch(/2h ago/);
  });

  it('returns fallback for invalid input', () => {
    expect(formatRelative('invalid')).toBe('—');
  });
});

describe('formatPct', () => {
  it('rounds to nearest integer', () => {
    expect(formatPct(45.7)).toBe('46%');
  });

  it('handles zero', () => {
    expect(formatPct(0)).toBe('0%');
  });

  it('handles 100', () => {
    expect(formatPct(100)).toBe('100%');
  });
});

describe('formatMissionId', () => {
  it('returns em dash for empty string', () => {
    expect(formatMissionId('')).toBe('—');
  });

  it('returns full id when <= 8 chars', () => {
    expect(formatMissionId('abc12345')).toBe('abc12345');
  });

  it('truncates long ids with ellipsis', () => {
    const long = 'abc12345-def6-7890-ghij-klmnopqrstuv';
    const result = formatMissionId(long);
    expect(result).toHaveLength(9); // 8 chars + ellipsis char
    expect(result).toContain('…');
  });
});

describe('formatProbability', () => {
  it('formats 0.5 as 50%', () => {
    expect(formatProbability(0.5)).toBe('50%');
  });

  it('formats 1.0 as 100%', () => {
    expect(formatProbability(1.0)).toBe('100%');
  });

  it('rounds fractional probabilities', () => {
    expect(formatProbability(0.756)).toBe('76%');
  });
});

describe('formatTemperature', () => {
  it('formats a temperature with one decimal', () => {
    expect(formatTemperature(145.6)).toBe('145.6 °C');
  });

  it('returns dash for null', () => {
    expect(formatTemperature(null)).toBe('—');
  });
});

describe('formatCoLevel', () => {
  it('formats CO level with one decimal', () => {
    expect(formatCoLevel(350.0)).toBe('350.0 ppm');
  });

  it('returns dash for null', () => {
    expect(formatCoLevel(null)).toBe('—');
  });
});

describe('formatSmokeDensity', () => {
  it('formats smoke density as a percentage', () => {
    expect(formatSmokeDensity(0.75)).toBe('75.0%');
  });

  it('returns dash for null', () => {
    expect(formatSmokeDensity(null)).toBe('—');
  });
});
