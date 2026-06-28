import type { Meta, StoryObj } from "@storybook/react-vite";
import { LogOut } from "lucide-react";

import { AppHeader } from "@/components/AppHeader";
import { Button } from "@/components/ui/button";

const meta = {
  title: "Components/AppHeader",
  component: AppHeader,
  tags: ["autodocs"],
  args: { subtitle: "Floci のローカル AWS で動くデバイス遠隔操作" },
} satisfies Meta<typeof AppHeader>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithAction: Story = {
  args: {
    action: (
      <Button variant="ghost" size="sm">
        <LogOut className="size-4" />
        ログアウト
      </Button>
    ),
  },
};
