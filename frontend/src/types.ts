export interface NetInterface {
  enabled: boolean;
  description: string;
  rx_bytes: number;
  tx_bytes: number;
}

export interface SystemStats {
  uptime_sec: number;
  cpu_percent: number;
  memory_percent: number;
}

export interface DeviceState {
  hostname: string;
  interfaces: Record<string, NetInterface>;
  system: SystemStats;
}

export interface ShadowDocument {
  state: {
    reported?: DeviceState;
    desired?: Partial<DeviceState>;
    delta?: Partial<DeviceState>;
  };
  metadata?: unknown;
  version: number;
  timestamp: number;
}

export interface Device {
  thingName: string;
  thingTypeName: string | null;
  connected: boolean;
}

export type CommandStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface Command {
  command_id: string;
  group_id: string;
  thing_name: string;
  command: string;
  status: CommandStatus;
  stdout: string;
  stderr: string;
  exit_code: number | null;
  duration_ms: number | null;
  created_at: string;
  updated_at: string;
}
