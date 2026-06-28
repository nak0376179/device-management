import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";

import { StatusBadge } from "@/components/StatusBadge";

const meta = {
  title: "Components/StatusBadge",
  component: StatusBadge,
  tags: ["autodocs"],
  args: { status: "running" },
} satisfies Meta<typeof StatusBadge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Pending: Story = { args: { status: "pending" } };
export const Completed: Story = { args: { status: "completed" } };
export const Failed: Story = { args: { status: "failed" } };

// Interaction test: the running badge renders its Japanese label.
export const Running: Story = {
  args: { status: "running" },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("実行中")).toBeInTheDocument();
  },
};

export const AllStatuses: Story = {
  render: () => (
    <div className="flex flex-wrap items-center gap-2">
      <StatusBadge status="pending" />
      <StatusBadge status="running" />
      <StatusBadge status="completed" />
      <StatusBadge status="failed" />
    </div>
  ),
};
