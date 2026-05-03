import type { Device, ShadowDocument } from './types';

const API_BASE = import.meta.env.VITE_API_URL ?? '/api';

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...((init?.headers as Record<string, string> | undefined) ?? {}),
  };
  if (init?.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export function listDevices(): Promise<{ devices: Device[] }> {
  return http('/devices');
}

export function getShadow(thingName: string): Promise<ShadowDocument> {
  return http(`/devices/${encodeURIComponent(thingName)}/shadow`);
}

export function setInterfaceEnabled(
  thingName: string,
  iface: string,
  enabled: boolean,
): Promise<ShadowDocument> {
  const action = enabled ? 'enable' : 'disable';
  return http(
    `/devices/${encodeURIComponent(thingName)}/interfaces/${encodeURIComponent(iface)}/${action}`,
    { method: 'POST' },
  );
}

export function setInterfaceDescription(
  thingName: string,
  iface: string,
  description: string,
): Promise<ShadowDocument> {
  return http(
    `/devices/${encodeURIComponent(thingName)}/interfaces/${encodeURIComponent(iface)}/description`,
    { method: 'PUT', body: JSON.stringify({ description }) },
  );
}
