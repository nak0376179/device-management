import { useState } from "react";
import { Loader2, MonitorSmartphone } from "lucide-react";

import { login } from "@/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface LoginFormProps {
  onLogin: (token: string) => void;
}

export function LoginForm({ onLogin }: LoginFormProps) {
  const [groupId, setGroupId] = useState("");
  const [groupPw, setGroupPw] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const token = await login(groupId, groupPw);
      onLogin(token);
    } catch {
      setError("グループ ID またはパスワードが正しくありません");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="bg-primary text-primary-foreground mx-auto mb-2 flex size-11 items-center justify-center rounded-xl">
            <MonitorSmartphone className="size-6" />
          </div>
          <CardTitle className="text-xl">Device Management</CardTitle>
          <CardDescription>グループの認証情報でログイン</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-2">
              <Label htmlFor="group-id">グループ ID</Label>
              <Input
                id="group-id"
                value={groupId}
                onChange={(e) => setGroupId(e.target.value)}
                autoFocus
                required
                aria-invalid={Boolean(error)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="group-pw">パスワード</Label>
              <Input
                id="group-pw"
                type="password"
                value={groupPw}
                onChange={(e) => setGroupPw(e.target.value)}
                required
                aria-invalid={Boolean(error)}
              />
            </div>
            {error && <p className="text-destructive text-sm">{error}</p>}
            <Button type="submit" disabled={loading} className="mt-1">
              {loading && <Loader2 className="size-4 animate-spin" />}
              {loading ? "ログイン中…" : "ログイン"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
