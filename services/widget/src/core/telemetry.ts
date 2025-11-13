import type { TelemetryEvent } from "../types";

const counters = {
  loads: 0,
  sessions: 0,
  messages: 0
};

export function recordMetric(event: TelemetryEvent["type"]) {
  switch (event) {
    case "widget_loaded":
      counters.loads += 1;
      break;
    case "session_started":
      counters.sessions += 1;
      break;
    case "message_sent":
      counters.messages += 1;
      break;
    default:
      break;
  }
  (window as typeof window & { __xinWidgetMetrics?: typeof counters }).__xinWidgetMetrics = counters;
}

export async function emitTelemetry(gatewayUrl: string, payload: TelemetryEvent) {
  recordMetric(payload.type);
  const endpoint = `${gatewayUrl.replace(/\/$/, "")}/widget/telemetry`;
  const body = JSON.stringify({ ...payload, ts: new Date().toISOString() });
  if (navigator.sendBeacon) {
    const blob = new Blob([body], { type: "application/json" });
    navigator.sendBeacon(endpoint, blob);
    return;
  }
  try {
    await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true
    });
  } catch {
    // swallow telemetry errors
  }
}
