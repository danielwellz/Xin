# Embed SDK (`/embed.js`)

The widget SDK lives under `services/widget`. It ships a <35&nbsp;kb (gzipped) bundle that exposes both vanilla and React entry points, handles signed handshake tokens, bilingual UX (English/Persian) and offline resilience.

## Quick Start

```bash
cd services/widget
pnpm install
pnpm build          # emits dist/xin-widget.* and bundle-report.html (when VITE_BUNDLE_REPORT=true)
pnpm test           # vitest (localisation + telemetry snapshots)
```

Serve `dist` behind `https://console.xinbot.ir/embed.js` (Docker/Helm frontend image already copies the build artefacts).

### Vanilla Snippet

```html
<script
  defer
  src="https://console.xinbot.ir/embed.js"
  data-tenant="TENANT_UUID"
  data-api="https://api.xinbot.ir"
  data-gateway="wss://gateway.xinbot.ir"
  data-locale="fa">
</script>
```

- `data-locale` can be `en` or `fa`; runtime toggle within the widget mirrors layout direction.
- `data-api` is used to fetch `/admin/tenants/{id}/embed_token` (signed, short-lived). Tokens never persist beyond memory.
- `data-gateway` opens a WebSocket at `/widget?tenant_id=…&token=…`.

### React Wrapper

```tsx
import { XinWidgetProvider, useXinBot } from "@xin-platform/widget-sdk/react";

function SupportLauncher() {
  const bot = useXinBot();
  return <button onClick={() => bot.open()}>Chat</button>;
}

export default function App() {
  return (
    <XinWidgetProvider
      options={{
        tenantId: "TENANT_UUID",
        apiBaseUrl: "https://api.xinbot.ir",
        gatewayUrl: "wss://gateway.xinbot.ir",
        theme: { primary: "#00AEEF" }
      }}
    >
      <SupportLauncher />
    </XinWidgetProvider>
  );
}
```

## Features

- **Theming** – Pass `theme` (primary colors, radius, launcher icon). Runtime CSS variables power the floating widget.
- **Handshake** – Calls `/admin/tenants/{id}/embed_token` with locale + optional identity payload `{ userId, name, email }`, then opens a WebSocket to the gateway. Exponential backoff + message queue handle transient failures.
- **Offline Fallback** – Displays a localized warning banner and queues outbound messages until the socket reconnects; queue flush occurs automatically.
- **Telemetry** – Emits `widget_loaded`, `session_started`, and `message_sent` events to `gateway/widget/telemetry` via `sendBeacon` (falls back to fetch) and exposes counters under `window.__xinWidgetMetrics` for Prometheus scrapers.
- **Locale Controls** – Built-in English/Persian system text plus overrides via `strings`. Layout direction flips automatically; hosts can call `controller.setLocale("fa")`.
- **SSR Safe** – Snippet auto-initialises when the script executes in the browser. Server-rendered pages simply include the `<script>` tag.

## Testing + Size Gate

- `pnpm build:report` generates `dist/bundle-report.html` with gzip/Brotli sizes (target <35&nbsp;kb gz for core bundle).
- Vitest snapshots cover locale merging and telemetry instrumentation.
- Example integration lives under `examples/widget-demo/index.html`.
