import { useEffect, useState } from 'react';
import { getTask } from '../api';
import type { Task } from '../types';

interface Props {
  thingName: string;
  taskId: string;
}

const POLL_MS = 3000;

export default function CommandResult({ thingName, taskId }: Props) {
  const [task, setTask] = useState<Task | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const data = await getTask(thingName, taskId);
        if (!cancelled) setTask(data);
        if (data.status === 'completed' || data.status === 'failed') return;
        if (!cancelled) setTimeout(poll, POLL_MS);
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    };

    poll();
    return () => { cancelled = true; };
  }, [thingName, taskId]);

  if (error) return <div className="error">{error}</div>;
  if (!task) return <div className="muted">送信中…</div>;

  const done = task.status === 'completed' || task.status === 'failed';
  return (
    <div className="cmd-result">
      <div className="cmd-meta">
        <span className={`cmd-status ${task.status}`}>{task.status}</span>
        {done && task.exit_code !== null && (
          <span className="muted"> exit {task.exit_code}</span>
        )}
        {done && task.duration_ms !== null && (
          <span className="muted"> {task.duration_ms}ms</span>
        )}
      </div>
      {!done && <div className="muted">実行中…</div>}
      {task.stdout && (
        <pre className="cmd-output stdout">{task.stdout}</pre>
      )}
      {task.stderr && (
        <pre className="cmd-output stderr">{task.stderr}</pre>
      )}
    </div>
  );
}
