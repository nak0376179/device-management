import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { listDevices, login, submitTask } from '@/api';

/** A minimal Response stand-in for the global fetch mock. */
function jsonResponse(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  return {
    ok: init.ok ?? true,
    status: init.status ?? 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as Response;
}

describe('api', () => {
  let store: Record<string, string>;

  beforeEach(() => {
    store = {};
    // api.ts reads/writes the JWT via localStorage, which doesn't exist in Node.
    vi.stubGlobal('localStorage', {
      getItem: (k: string) => store[k] ?? null,
      setItem: (k: string, v: string) => {
        store[k] = v;
      },
      removeItem: (k: string) => {
        delete store[k];
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('login posts the credentials and stores the returned jwt', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ token: 'jwt-123' }));
    vi.stubGlobal('fetch', fetchMock);

    const token = await login('dev-group', 'devpass');

    expect(token).toBe('jwt-123');
    expect(store.jwt).toBe('jwt-123');
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/auth/login');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body as string)).toEqual({
      group_id: 'dev-group',
      group_pw: 'devpass',
    });
  });

  it('login rejects on a non-ok response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({}, { ok: false, status: 401 })));

    await expect(login('x', 'y')).rejects.toThrow('認証に失敗しました');
  });

  it('listDevices attaches the bearer token from storage', async () => {
    store.jwt = 'jwt-abc';
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ devices: [] }));
    vi.stubGlobal('fetch', fetchMock);

    await listDevices();

    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/devices');
    expect((opts.headers as Record<string, string>).Authorization).toBe('Bearer jwt-abc');
  });

  it('submitTask url-encodes the thing name and sends a JSON body', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ task_id: 't1' }));
    vi.stubGlobal('fetch', fetchMock);

    const out = await submitTask('dev-group:dead', 'uname -a');

    expect(out).toEqual({ task_id: 't1' });
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/devices/dev-group%3Adead/tasks');
    expect((opts.headers as Record<string, string>)['Content-Type']).toBe('application/json');
    expect(JSON.parse(opts.body as string)).toEqual({ command: 'uname -a' });
  });
});
