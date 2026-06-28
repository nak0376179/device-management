import { useEffect, useState } from "react";

import { getTask } from "@/api";
import { isTerminal, type Task } from "@/types";
import { StatusBadge } from "@/components/StatusBadge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export interface CommandResultProps {
  thingName: string;
  taskId: string;
}

const POLL_MS = 3000;

function Output({ text, stderr = false }: { text: string; stderr?: boolean }) {
  return (
    <pre
      className={
        "bg-muted/60 max-h-72 overflow-auto rounded-md px-3 py-2 font-mono text-xs break-all whitespace-pre-wrap " +
        (stderr ? "text-destructive" : "text-foreground")
      }
    >
      {text}
    </pre>
  );
}

export function CommandResult({ thingName, taskId }: CommandResultProps) {
  const [task, setTask] = useState<Task | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const data = await getTask(thingName, taskId);
        if (cancelled) return;
        setTask(data);
        if (isTerminal(data.status)) return;
        setTimeout(poll, POLL_MS);
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    };

    void poll();
    return () => {
      cancelled = true;
    };
  }, [thingName, taskId]);

  if (error) {
    return (
      <Card className="border-destructive/40 py-4">
        <CardContent className="text-destructive text-sm">{error}</CardContent>
      </Card>
    );
  }

  if (!task) {
    return (
      <Card className="gap-3 py-4">
        <CardContent className="flex flex-col gap-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-12 w-full" />
        </CardContent>
      </Card>
    );
  }

  const done = isTerminal(task.status);

  return (
    <Card className="gap-3 py-4">
      <CardHeader className="flex flex-row items-center gap-2 px-4">
        <StatusBadge status={task.status} />
        {done && task.exit_code !== null && (
          <span className="text-muted-foreground text-xs">
            exit {task.exit_code}
          </span>
        )}
        {done && task.duration_ms !== null && (
          <span className="text-muted-foreground text-xs tabular-nums">
            {task.duration_ms}ms
          </span>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-2 px-4">
        <code className="text-muted-foreground font-mono text-xs">
          $ {task.command}
        </code>
        {task.stdout && <Output text={task.stdout} />}
        {task.stderr && <Output text={task.stderr} stderr />}
      </CardContent>
    </Card>
  );
}
