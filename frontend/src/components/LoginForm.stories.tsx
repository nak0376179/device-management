import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import { LoginForm } from "@/components/LoginForm";

const meta = {
  title: "Components/LoginForm",
  component: LoginForm,
  tags: ["autodocs"],
  parameters: { layout: "fullscreen" },
  args: { onLogin: fn() },
} satisfies Meta<typeof LoginForm>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

// Interaction test: the labelled fields accept input (stops short of submitting,
// which would hit the network).
export const FillForm: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const groupId = canvas.getByLabelText("グループ ID");
    const password = canvas.getByLabelText("パスワード");
    await userEvent.type(groupId, "dev-group");
    await userEvent.type(password, "devpass");
    await expect(groupId).toHaveValue("dev-group");
    await expect(password).toHaveValue("devpass");
  },
};
