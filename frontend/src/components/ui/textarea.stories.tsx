import type { Meta, StoryObj } from "@storybook/react-vite";

import { Textarea } from "@/components/ui/textarea";

const meta = {
  title: "UI/Textarea",
  component: Textarea,
  tags: ["autodocs"],
  args: { placeholder: "実行するコマンドを入力 (例: uname -a)", rows: 3 },
} satisfies Meta<typeof Textarea>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Mono: Story = { args: { className: "font-mono" } };
export const Disabled: Story = { args: { disabled: true } };
