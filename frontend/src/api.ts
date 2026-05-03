import type { Command, Device, ShadowDocument } from './types';

const API_BASE = import.meta.env.VITE_API_URL ?? '/api';

function getToken(): string | null {
  return localStorage.getItem('jwt');
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...((init?.headers as Record<string, string> | undefined) ?? {}),
  };
  if (init?.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (res.status === 401) {
    localStorage.removeItem('jwt');
    window.location.reload();
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function login(group_id: string, group_pw: string): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ group_id, group_pw }),
  });
  if (!res.ok) throw new Error('認証に失敗しました');
  const { token } = await res.json();
  localStorage.setItem('jwt', token);
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

export function submitCommand(thingName: string, command: string): Promise<{ command_id: string }> {
  return http(`/devices/${encodeURIComponent(thingName)}/commands`, {
    method: 'POST',
    body: JSON.stringify({ command }),
  });
}

export function getCommand(commandId: string): Promise<Command> {
  return http(`/commands/${encodeURIComponent(commandId)}`);
}

export function listCommands(thingName: string): Promise<{ commands: Command[] }> {
  return http(`/devices/${encodeURIComponent(thingName)}/commands`);
}
