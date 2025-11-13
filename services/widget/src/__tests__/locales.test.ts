import { describe, expect, it } from "vitest";

import { resolveStrings, toggleLocale } from "../core/locales";
import type { WidgetOptions } from "../types";

const baseOptions: WidgetOptions = {
  tenantId: "tenant",
  apiBaseUrl: "https://api.example.com",
  gatewayUrl: "wss://gateway.example.com"
};

describe("locales", () => {
  it("toggles between en and fa", () => {
    expect(toggleLocale("en")).toBe("fa");
    expect(toggleLocale("fa")).toBe("en");
  });

  it("merges overrides", () => {
    const { strings } = resolveStrings("fa", {
      ...baseOptions,
      strings: {
        fa: { send: "ارسال کن" }
      }
    });
    expect(strings.send).toBe("ارسال کن");
  });
});
