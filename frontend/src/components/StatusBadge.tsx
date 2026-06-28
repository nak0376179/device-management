import { CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import type { TaskStatus } from "@/types";

const STYLES: Record<TaskStatus, string> = {
  pending: "bg-status-pending-bg text-status-pending",
  running: "bg-status-running-bg text-status-running",
  completed: "bg-status-completed-bg text-status-completed",
  failed: "bg-status-failed-bg text-status-failed",
};

const LABEL: Record<TaskStatus, string> = {
  pending: "待機中",
  running: "実行中",
  completed: "完了",
  failed: "失敗",
};

const ICON: Record<TaskStatus, typeof Clock> = {
  pending: Clock,
  running: Loader2,
  completed: CheckCircle2,
  failed: XCircle,
};

export interface StatusBadgeProps {
  status: TaskStatus;
  className?: string;
}

/** Color-coded command task lifecycle indicator (待機中 / 実行中 / 完了 / 失敗). */
export function StatusBadge({ status, className }: StatusBadgeProps) {
  const Icon = ICON[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold",
        STYLES[status],
        className,
      )}
    >
      <Icon className={cn("size-3", status === "running" && "animate-spin")} />
      {LABEL[status]}
    </span>
  );
}
