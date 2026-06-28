import { type ReactNode } from "react";
import { MonitorSmartphone } from "lucide-react";

export interface AppHeaderProps {
  title?: string;
  subtitle?: string;
  /** Slot for actions (e.g. theme toggle, logout). */
  action?: ReactNode;
}

/** App title block with an optional action slot. */
export function AppHeader({
  title = "Device Management",
  subtitle,
  action,
}: AppHeaderProps) {
  return (
    <header className="flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <div className="bg-primary text-primary-foreground flex size-9 items-center justify-center rounded-lg">
          <MonitorSmartphone className="size-5" />
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight">{title}</h1>
          {subtitle && (
            <p className="text-muted-foreground text-xs">{subtitle}</p>
          )}
        </div>
      </div>
      {action && <div className="flex items-center gap-1">{action}</div>}
    </header>
  );
}
