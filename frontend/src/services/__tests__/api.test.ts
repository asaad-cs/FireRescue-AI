import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  startMission,
  endMission,
  pauseMission,
  resumeMission,
  getHealth,
} from '@/services/api';

// ── Mock fetch ─────────────────────────────────────────────────────────────────

function mockFetch(status: number, body: unknown = null) {
  const text = body === null ? '' : JSON.stringify(body);
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      text: () => Promise.resolve(text),
    }),
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ── Tests ──────────────────────────────────────────────────────────────────────

describe('api — startMission', () => {
  it('calls POST /api/mission/start', async () => {
    mockFetch(200, { status: 'started', mission_id: 'abc' });
    await startMission();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/mission/start',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('throws on 409 Conflict', async () => {
    mockFetch(409, { detail: 'Mission already active' });
    await expect(startMission()).rejects.toThrow('409');
  });

  it('throws on network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network error')));
    await expect(startMission()).rejects.toThrow('Network error');
  });
});

describe('api — pauseMission', () => {
  it('calls POST /api/mission/pause', async () => {
    mockFetch(200, { status: 'paused', mission_id: 'abc' });
    await pauseMission();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/mission/pause',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('throws on non-2xx response', async () => {
    mockFetch(409, { detail: 'Cannot pause' });
    await expect(pauseMission()).rejects.toThrow('409');
  });
});

describe('api — resumeMission', () => {
  it('calls POST /api/mission/resume', async () => {
    mockFetch(200, { status: 'resumed', mission_id: 'abc' });
    await resumeMission();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/mission/resume',
      expect.objectContaining({ method: 'POST' }),
    );
  });
});

describe('api — endMission', () => {
  it('calls POST /api/mission/end', async () => {
    mockFetch(200, { status: 'ended', mission_id: 'abc' });
    await endMission();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/mission/end',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('resolves with no return value on success', async () => {
    mockFetch(200, { status: 'ended', mission_id: 'abc' });
    const result = await endMission();
    expect(result).toBeUndefined();
  });
});

describe('api — getHealth', () => {
  it('returns status from /api/health', async () => {
    mockFetch(200, { status: 'ok' });
    const result = await getHealth();
    expect(result).toEqual({ status: 'ok' });
  });

  it('throws on 500', async () => {
    mockFetch(500);
    await expect(getHealth()).rejects.toThrow('500');
  });
});
