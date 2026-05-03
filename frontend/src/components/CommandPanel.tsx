import { useState } from 'react';
import { submitCommand } from '../api';
import CommandResult from './CommandResult';

interface Props {
  thingName: string;
}

export default function CommandPanel({ thingName }: Props) {
  const [command, setCommand] = useState('');
  const [commandIds, setCommandIds] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!command.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const { command_id } = await submitCommand(thingName, command.trim());
      setCommandIds((prev) => [command_id, ...prev]);
      setCommand('');
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section>
      <h3>コマンド実行</h3>
      <form className="cmd-form" onSubmit={handleSubmit}>
        <textarea
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          placeholder="実行するコマンドを入力 (例: uname -a)"
          rows={2}
        />
        <button type="submit" disabled={submitting || !command.trim()}>
          {submitting ? '送信中…' : '実行'}
        </button>
      </form>
      {error && <div className="error">{error}</div>}
      <div className="cmd-history">
        {commandIds.map((id) => (
          <CommandResult key={id} commandId={id} />
        ))}
      </div>
    </section>
  );
}
