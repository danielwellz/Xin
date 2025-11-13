import { GatewayConnection } from "./core/connection";
import { resolveStrings, toggleLocale } from "./core/locales";
import { applyTheme } from "./core/theme";
import { emitTelemetry } from "./core/telemetry";
import type { Locale, WidgetController, WidgetOptions } from "./types";
import widgetCss from "./styles/widget.css?inline";

const DEFAULT_LOCALE: Locale = "en";

class WidgetInstance implements WidgetController {
  #root: HTMLElement;
  #shadow: ShadowRoot;
  #launcher: HTMLButtonElement;
  #panel: HTMLDivElement;
  #messages: HTMLDivElement;
  #textarea: HTMLTextAreaElement;
  #offlineBanner: HTMLDivElement;
  #localeButton: HTMLButtonElement;
  #options: WidgetOptions;
  #locale: Locale;
  #strings: ReturnType<typeof resolveStrings>["strings"];
  #connection: GatewayConnection;
  #open = false;
  #sessionStarted = false;

  constructor(options: WidgetOptions) {
    this.#options = options;
    this.#locale = options.locale ?? options.defaultLocale ?? DEFAULT_LOCALE;
    const resolved = resolveStrings(this.#locale, options);
    this.#strings = resolved.strings;

    this.#root = options.container ?? document.createElement("div");
    if (!options.container) {
      document.body.appendChild(this.#root);
    }
    this.#shadow = this.#root.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = widgetCss;
    this.#shadow.appendChild(style);

    this.#offlineBanner = document.createElement("div");
    this.#offlineBanner.className = "xin-offline";
    this.#offlineBanner.textContent = this.#strings.offline;
    this.#offlineBanner.style.display = "none";

    this.#messages = document.createElement("div");
    this.#messages.className = "xin-messages";
    this.#messages.setAttribute("role", "log");
    this.#messages.setAttribute("aria-live", "polite");

    this.#textarea = document.createElement("textarea");
    this.#textarea.placeholder = this.#strings.placeholder;
    this.#textarea.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        void this.send();
      }
    });

    const sendButton = document.createElement("button");
    sendButton.type = "button";
    sendButton.textContent = this.#strings.send;
    sendButton.addEventListener("click", () => void this.send());

    const localeButton = document.createElement("button");
    localeButton.type = "button";
    localeButton.title = this.#strings.localeToggle;
    localeButton.textContent = this.#locale === "en" ? "FA" : "EN";
    localeButton.addEventListener("click", () => {
      this.setLocale(toggleLocale(this.#locale));
    });
    this.#localeButton = localeButton;

    const input = document.createElement("div");
    input.className = "xin-input";
    input.appendChild(this.#textarea);
    input.appendChild(sendButton);

    const header = document.createElement("div");
    header.className = "xin-header";
    const title = document.createElement("strong");
    title.textContent = this.#strings.launcherLabel;
    const closeButton = document.createElement("button");
    closeButton.type = "button";
    closeButton.innerHTML = "&times;";
    closeButton.addEventListener("click", () => this.close());
    header.appendChild(title);
    header.appendChild(localeButton);
    header.appendChild(closeButton);

    this.#panel = document.createElement("div");
    this.#panel.className = "xin-panel hidden";
    this.#panel.appendChild(this.#offlineBanner);
    this.#panel.appendChild(header);
    this.#panel.appendChild(this.#messages);
    this.#panel.appendChild(input);

    this.#launcher = document.createElement("button");
    this.#launcher.className = "xin-launcher";
    this.#launcher.setAttribute("aria-label", this.#strings.launcherLabel);
    this.#launcher.textContent = this.#options.theme?.launcherIcon ?? "✉️";
    this.#launcher.addEventListener("click", () => (this.#open ? this.close() : this.open()));

    this.#shadow.appendChild(this.#panel);
    this.#shadow.appendChild(this.#launcher);

    applyTheme(this.#shadow.host as HTMLElement, this.#options.theme);

    this.#connection = new GatewayConnection({
      apiBaseUrl: options.apiBaseUrl,
      gatewayUrl: options.gatewayUrl,
      tenantId: options.tenantId,
      locale: this.#locale,
      identity: options.identity,
      callbacks: {
        onOpen: () => this.#setOffline(false),
        onClose: () => this.#setOffline(true),
        onMessage: (payload) => this.#appendMessage(payload, "agent"),
        onError: () => this.#setOffline(true)
      }
    });
  }

  async init() {
    try {
      await this.#connection.start();
      this.#appendMessage(this.#strings.welcome, "agent");
    } catch (error) {
      this.#setOffline(true);
      this.#appendMessage(this.#strings.reconnecting, "agent");
      console.warn("Failed to start Xin widget connection", error);
    } finally {
      await this.#emitTelemetry({
        type: "widget_loaded",
        tenantId: this.#options.tenantId
      });
    }
  }

  open() {
    this.#panel.classList.remove("hidden");
    this.#panel.setAttribute("dir", this.#locale === "fa" ? "rtl" : "ltr");
    this.#open = true;
    if (!this.#sessionStarted) {
      this.#sessionStarted = true;
      void this.#emitTelemetry({
        type: "session_started",
        tenantId: this.#options.tenantId,
        locale: this.#locale
      });
    }
  }

  close() {
    this.#panel.classList.add("hidden");
    this.#open = false;
  }

  setLocale(locale: Locale) {
    this.#locale = locale;
    const resolved = resolveStrings(locale, this.#options);
    this.#strings = resolved.strings;
    this.#textarea.placeholder = this.#strings.placeholder;
    this.#launcher.setAttribute("aria-label", this.#strings.launcherLabel);
    this.#localeButton.textContent = locale === "en" ? "FA" : "EN";
    this.#panel.setAttribute("dir", locale === "fa" ? "rtl" : "ltr");
  }

  async sendMessage(message: string) {
    if (!message.trim()) {
      return;
    }
    this.#appendMessage(message, "user");
    const payload = JSON.stringify({
      message,
      tenant_id: this.#options.tenantId,
      locale: this.#locale,
      identity: this.#options.identity ?? null
    });
    const start = performance.now();
    await this.#connection.send(payload);
    const latency = Math.round(performance.now() - start);
    void this.#emitTelemetry({
      type: "message_sent",
      tenantId: this.#options.tenantId,
      latency_ms: latency
    });
  }

  async send() {
    const value = this.#textarea.value.trim();
    if (!value) {
      return;
    }
    this.#textarea.value = "";
    await this.sendMessage(value);
  }

  destroy() {
    this.#connection.stop();
    this.#root.remove();
  }

  #appendMessage(text: string, variant: "agent" | "user") {
    const bubble = document.createElement("div");
    bubble.className = `xin-message ${variant}`;
    bubble.textContent = text;
    this.#messages.appendChild(bubble);
    this.#messages.scrollTop = this.#messages.scrollHeight;
  }

  #setOffline(off: boolean) {
    this.#offlineBanner.style.display = off ? "flex" : "none";
  }

  async #emitTelemetry(payload: Parameters<typeof emitTelemetry>[1]) {
    if (this.#options.enableTelemetry === false) {
      return;
    }
    await emitTelemetry(this.#options.gatewayUrl, payload);
  }
}

const XinBot = {
  init: async (options: WidgetOptions): Promise<WidgetController> => {
    const instance = new WidgetInstance(options);
    await instance.init();
    return instance;
  }
};

export type { WidgetOptions, WidgetController } from "./types";
export { toggleLocale, DEFAULT_LOCALE };
export default XinBot;
export const init = XinBot.init;

declare global {
  interface Window {
    XinBot?: typeof XinBot;
  }
}

if (typeof window !== "undefined") {
  window.XinBot = XinBot;
  const script = document.currentScript as HTMLScriptElement | null;
  if (script?.dataset?.tenant && !script.dataset.autoinitDisabled) {
    const tenantId = script.dataset.tenant;
    const apiBaseUrl = script.dataset.api ?? window.location.origin;
    const gatewayUrl = script.dataset.gateway ?? apiBaseUrl.replace(/^http/, "ws");
    const locale = (script.dataset.locale as Locale | undefined) ?? DEFAULT_LOCALE;
    void XinBot.init({
      tenantId,
      apiBaseUrl,
      gatewayUrl,
      locale
    });
  }
}
