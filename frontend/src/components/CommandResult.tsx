import { useEffect, useState } from 'react';
import { getCommand } from '../api';
import type { Command } from '../types';

interface Props {
  commandId: string;
}

const POLL_MS = 3000;

export default function CommandResult({ commandId }: Props) {
  const [cmd, setCmd] = useState<Command | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const data = await getCommand(commandId);
        if (!cancelled) setCmd(data);
        if (data.status === 'completed' || data.status === 'failed') return;
        if (!cancelled) setTimeout(poll, POLL_MS);
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    };

    poll();
    return () => { cancelled = true; };
  }, [commandId]);

  if (error) return <div className="error">{error}</div>;
  if (!cmd) return <div className="muted">送信中…</div>;

  const done = cmd.status === 'completed' || cmd.status === 'failed';
  return (
    <div className="cmd-result">
      <div className="cmd-meta">
        <span className={`cmd-status ${cmd.status}`}>{cmd.status}</span>
        {done && cmd.exit_code !== null && (
          <span className="muted"> exit {cmd.exit_code}</span>
        )}
        {done && cmd.duration_ms !== null && (
          <span className="muted"> {cmd.duration_ms}ms</span>
        )}
      </div>
      {!done && <div className="muted">実行中…</div>}
      {cmd.stdout && (
        <pre className="cmd-output stdout">{cmd.stdout}</pre>
      )}
      {cmd.stderr && (
        <pre className="cmd-output stderr">{cmd.stderr}</pre>
      )}
    </div>
  );
}
