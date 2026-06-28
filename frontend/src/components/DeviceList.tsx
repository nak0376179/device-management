import { cn } from "@/lib/utils";
import type { Device } from "@/types";

export interface DeviceListProps {
  devices: Device[];
  selected: string | null;
  onSelect: (thingName: string) => void;
}

/** Sidebar list of devices with a live connectivity dot. */
export function DeviceList({ devices, selected, onSelect }: DeviceListProps) {
  if (devices.length === 0) {
    return (
      <p className="text-muted-foreground px-2 py-4 text-sm">デバイスがありません</p>
    );
  }

  return (
    <ul className="flex flex-col gap-1">
      {devices.map((d) => {
        const active = selected === d.thingName;
        return (
          <li key={d.thingName}>
            <button
              type="button"
              onClick={() => onSelect(d.thingName)}
              aria-current={active}
              className={cn(
                "flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors",
                "hover:bg-accent hover:text-accent-foreground",
                active && "bg-accent text-accent-foreground font-medium",
              )}
            >
              <span
                aria-hidden
                className={cn(
                  "size-2 shrink-0 rounded-full",
                  d.connected
                    ? "bg-status-online shadow-[0_0_0_3px] shadow-status-online-bg"
                    : "bg-status-offline",
                )}
              />
              <span className="truncate font-mono text-xs">{d.thingName}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
