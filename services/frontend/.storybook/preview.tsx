import type { Preview } from "@storybook/react";

import "../src/styles/global.css";
import "../src/i18n/config";

import { LocaleProvider } from "@/features/i18n/LocaleProvider";

const preview: Preview = {
  decorators: [
    (Story) => (
      <LocaleProvider>
        <div className="p-6">
          <Story />
        </div>
      </LocaleProvider>
    )
  ]
};

export default preview;
