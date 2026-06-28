import type { Meta, StoryObj } from "@storybook/react-vite";

import { LoginForm } from "@/components/LoginForm";

const meta = {
  title: "Components/LoginForm",
  component: LoginForm,
  tags: ["autodocs"],
  parameters: { layout: "fullscreen" },
  args: { onLogin: () => {} },
} satisfies Meta<typeof LoginForm>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
