export type Locale = "en" | "fa";

export type LocaleStrings = {
  launcherLabel: string;
  placeholder: string;
  send: string;
  reconnecting: string;
  offline: string;
  welcome: string;
  sessionStarted: string;
  localeToggle: string;
};

export type ThemeConfig = Partial<{
  primary: string;
  primaryContrast: string;
  surface: string;
  surfaceAlt: string;
  text: string;
  radius: number;
  launcherIcon: string;
}>;

export type Identity = {
  userId?: string;
  name?: string;
  email?: string;
};

export type WidgetOptions = {
  tenantId: string;
  apiBaseUrl: string;
  gatewayUrl: string;
  locale?: Locale;
  defaultLocale?: Locale;
  theme?: ThemeConfig;
  container?: HTMLElement | null;
  strings?: Partial<Record<Locale, Partial<LocaleStrings>>>;
  identity?: Identity;
  enableTelemetry?: boolean;
};

export type WidgetController = {
  open: () => void;
  close: () => void;
  setLocale: (locale: Locale) => void;
  sendMessage: (message: string) => Promise<void>;
  destroy: () => void;
};

export type TokenResponse = {
  token: string;
  expires_at: string;
};

export type TelemetryEvent =
  | { type: "widget_loaded"; tenantId: string }
  | { type: "session_started"; tenantId: string; locale: Locale }
  | { type: "message_sent"; tenantId: string; latency_ms: number };
