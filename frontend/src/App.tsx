import { useEffect, useState } from "react";
import { LogOut } from "lucide-react";

import * as api from "@/api";
import type { Device } from "@/types";
import { AppHeader } from "@/components/AppHeader";
import { CommandPanel } from "@/components/CommandPanel";
import { DeviceList } from "@/components/DeviceList";
import { LoginForm } from "@/components/LoginForm";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export default function App() {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem("jwt"),
  );
  const [devices, setDevices] = useState<Device[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleLogout() {
    localStorage.removeItem("jwt");
    setToken(null);
    setDevices([]);
    setSelected(null);
  }

  useEffect(() => {
    if (!token) return;
    api
      .listDevices()
      .then((res) => {
        setDevices(res.devices);
        setSelected((cur) => cur ?? res.devices[0]?.thingName ?? null);
      })
      .catch((e) => setError(String(e)));
  }, [token]);

  if (!token) {
    return <LoginForm onLogin={setToken} />;
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col gap-4 px-4 py-6">
      <AppHeader
        subtitle="Floci のローカル AWS で動くデバイス遠隔操作"
        action={
          <>
            <ThemeToggle />
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              <LogOut className="size-4" />
              ログアウト
            </Button>
          </>
        }
      />

      <Separator />

      <div className="grid flex-1 gap-4 md:grid-cols-[220px_1fr]">
        <aside>
          <h2 className="text-muted-foreground mb-2 px-1 text-xs font-semibold tracking-wide uppercase">
            デバイス
          </h2>
          <DeviceList
            devices={devices}
            selected={selected}
            onSelect={setSelected}
          />
        </aside>

        <main className="flex flex-col gap-4">
          {error && (
            <Card className="border-destructive/40 text-destructive px-4 py-3 text-sm">
              {error}
            </Card>
          )}
          {selected ? (
            <CommandPanel thingName={selected} />
          ) : (
            <p className="text-muted-foreground text-sm">
              デバイスを選択してください
            </p>
          )}
        </main>
      </div>
    </div>
  );
}
