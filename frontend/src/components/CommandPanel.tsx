import { useState } from "react";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";

import { submitTask } from "@/api";
import { CommandResult } from "@/components/CommandResult";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export interface CommandPanelProps {
  thingName: string;
}

export function CommandPanel({ thingName }: CommandPanelProps) {
  const [command, setCommand] = useState("");
  const [taskIds, setTaskIds] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!command.trim()) return;
    setSubmitting(true);
    try {
      const { task_id } = await submitTask(thingName, command.trim());
      setTaskIds((prev) => [task_id, ...prev]);
      setCommand("");
      toast.success("コマンドを送信しました");
    } catch (err) {
      toast.error("送信に失敗しました", { description: String(err) });
    } finally {
      setSubmitting(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    // Cmd/Ctrl+Enter to submit, matching common terminal/editor ergonomics.
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      void handleSubmit(e as unknown as React.FormEvent);
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <form className="flex items-end gap-2" onSubmit={handleSubmit}>
        <Textarea
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="実行するコマンドを入力 (例: uname -a)  —  ⌘/Ctrl + Enter で実行"
          rows={2}
          className="font-mono"
        />
        <Button type="submit" disabled={submitting || !command.trim()}>
          {submitting ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Play className="size-4" />
          )}
          実行
        </Button>
      </form>

      <div className="flex flex-col gap-3">
        {taskIds.map((id) => (
          <CommandResult key={id} thingName={thingName} taskId={id} />
        ))}
      </div>
    </section>
  );
}
