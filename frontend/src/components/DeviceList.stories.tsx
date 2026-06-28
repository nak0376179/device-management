import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";

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
