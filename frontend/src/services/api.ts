/**
 * REST API client — thin wrapper over fetch for mission control.
 *
 * All calls route through the Vite dev-server proxy:
 *   /api/* → http://localhost:8000/* (prefix stripped)
 *
 * Errors are surfaced as thrown Error objects; callers handle them.
 */

const BASE = '/api';

async function request(method: string, path: string): Promise<unknown> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`${method} ${path} → ${res.status}: ${body}`);
  }
  // Some endpoints return no body (204) or minimal JSON
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

export async function startMission(): Promise<void> {
  await request('POST', '/mission/start');
}

export async function endMission(): Promise<void> {
  await request('POST', '/mission/end');
}

export async function pauseMission(): Promise<void> {
  await request('POST', '/mission/pause');
}

export async function resumeMission(): Promise<void> {
  await request('POST', '/mission/resume');
}

export async function getHealth(): Promise<{ status: string }> {
  const data = await request('GET', '/health');
  return data as { status: string };
}
