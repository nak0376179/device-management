export interface Device {
  thingName: string;
  thingTypeName: string | null;
  connected: boolean;
}

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface Task {
  device_pk: string;
  task_id: string;
  group_id: string;
  command: string;
  status: TaskStatus;
  stdout: string;
  stderr: string;
  exit_code: number | null;
  duration_ms: number | null;
  updated_at: string;
}
