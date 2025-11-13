import { describe, expect, it, vi } from "vitest";

import { emitTelemetry } from "../core/telemetry";

describe("telemetry", () => {
  it("uses sendBeacon when available", async () => {
    const spy = vi.fn();
    Object.defineProperty(navigator, "sendBeacon", {
      writable: true,
      value: spy
    });
    await emitTelemetry("https://gateway.example.com", {
      type: "widget_loaded",
      tenantId: "tenant"
    });
    expect(spy).toHaveBeenCalledOnce();
  });
});
