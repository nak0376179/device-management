import type { Meta, StoryObj } from "@storybook/react-vite";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const meta = {
  title: "UI/Card",
  component: Card,
  tags: ["autodocs"],
} satisfies Meta<typeof Card>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <Card className="w-80">
      <CardHeader>
        <CardTitle>deadbeef0101</CardTitle>
        <CardDescription>dev-group のデバイス</CardDescription>
      </CardHeader>
      <CardContent className="text-muted-foreground text-sm">
        最後のコマンド: uname -a（完了, exit 0）
      </CardContent>
      <CardFooter>
        <Button size="sm">コマンド実行</Button>
      </CardFooter>
    </Card>
  ),
};
