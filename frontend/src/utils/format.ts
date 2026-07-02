/** Formatting helpers shared across all dashboard components. */

export function formatElapsed(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return [h, m, sec].map((v) => String(v).padStart(2, '0')).join(':');
}

export function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '--:--:--';
    return d.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return '--:--:--';
  }
}

export function formatRelative(iso: string): string {
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '—';
    const diff = Math.floor((Date.now() - d.getTime()) / 1000);
    if (diff < 5) return 'just now';
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
  } catch {
    return '—';
  }
}

export function formatPct(value: number): string {
  return `${Math.round(value)}%`;
}

/** Shorten a UUID-style mission ID for compact display: "M-a3f2…" */
export function formatMissionId(id: string): string {
  if (!id) return '—';
  if (id.length <= 8) return id;
  return id.substring(0, 8) + '…';
}

/** Format victim probability as a percentage string with one decimal. */
export function formatProbability(p: number): string {
  return `${(p * 100).toFixed(0)}%`;
}

export function formatTemperature(v: number | null): string {
  return v === null ? '—' : `${v.toFixed(1)} °C`;
}

export function formatCoLevel(v: number | null): string {
  return v === null ? '—' : `${v.toFixed(1)} ppm`;
}

export function formatSmokeDensity(v: number | null): string {
  return v === null ? '—' : `${(v * 100).toFixed(1)}%`;
}
