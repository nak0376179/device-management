import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import { DeviceList } from "@/components/DeviceList";
import type { Device } from "@/types";

const DEVICES: Device[] = [
  { thingName: "dev-group:deadbeef0101", thingTypeName: null, connected: true },
  { thingName: "dev-group:deadbeef0102", thingTypeName: null, connected: false },
  { thingName: "dev-group:cafef00d0001", thingTypeName: null, connected: true },
];

const meta = {
  title: "Components/DeviceList",
  component: DeviceList,
  tags: ["autodocs"],
  args: { devices: DEVICES, selected: DEVICES[0].thingName, onSelect: () => {} },
} satisfies Meta<typeof DeviceList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => {
    const [selected, setSelected] = useState<string | null>(
      DEVICES[0].thingName,
    );
    return (
      <div className="w-60">
        <DeviceList
          devices={DEVICES}
          selected={selected}
          onSelect={setSelected}
        />
      </div>
    );
  },
};

export const Empty: Story = {
  render: () => (
    <div className="w-60">
      <DeviceList devices={[]} selected={null} onSelect={() => {}} />
    </div>
  ),
};

// Interaction test: clicking a row calls onSelect with that device's thingName.
export const Interactive: Story = {
  args: { devices: DEVICES, selected: DEVICES[0].thingName, onSelect: fn() },
  render: (args) => (
    <div className="w-60">
      <DeviceList {...args} />
    </div>
  ),
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByText(DEVICES[1].thingName));
    await expect(args.onSelect).toHaveBeenCalledWith(DEVICES[1].thingName);
  },
};
