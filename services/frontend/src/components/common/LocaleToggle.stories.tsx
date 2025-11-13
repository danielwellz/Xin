import type { Meta, StoryObj } from "@storybook/react";

import { LocaleToggle } from "./LocaleToggle";
import { LocaleProvider } from "@/features/i18n/LocaleProvider";

const meta: Meta<typeof LocaleToggle> = {
  title: "Common/LocaleToggle",
  component: LocaleToggle,
  decorators: [(Story) => <LocaleProvider><Story /></LocaleProvider>]
};

export default meta;

type Story = StoryObj<typeof LocaleToggle>;

export const Default: Story = {
  render: () => <LocaleToggle />
};
