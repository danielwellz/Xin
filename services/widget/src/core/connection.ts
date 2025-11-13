import type { Identity, Locale, TokenResponse } from "../types";

type ConnectionCallbacks = {
  onOpen: () => void;
  onClose: () => void;
  onMessage: (payload: string) => void;
  onError: (error: Error) => void;
};

export class GatewayConnection {
  #apiBaseUrl: string;
  #gatewayUrl: string;
  #tenantId: string;
  #locale: Locale;
  #identity?: Identity;
  #callbacks: ConnectionCallbacks;
  #ws: WebSocket | null = null;
  #token: string | null = null;
  #expiresAt: number | null = null;
  #queue: string[] = [];
  #attempt = 0;
  #closed = false;

  constructor(params: {
    apiBaseUrl: string;
    gatewayUrl: string;
    tenantId: string;
    locale: Locale;
    identity?: Identity;
    callbacks: ConnectionCallbacks;
  }) {
    this.#apiBaseUrl = params.apiBaseUrl.replace(/\/$/, "");
    this.#gatewayUrl = params.gatewayUrl.replace(/\/$/, "");
    this.#tenantId = params.tenantId;
    this.#locale = params.locale;
    this.#identity = params.identity;
    this.#callbacks = params.callbacks;
  }

  async start() {
    this.#closed = false;
    await this.#ensureToken();
    this.#connect();
  }

  stop() {
    this.#closed = true;
    this.#ws?.close();
  }

  async send(payload: string) {
    if (!this.#ws || this.#ws.readyState !== WebSocket.OPEN) {
      this.#queue.push(payload);
      return;
    }
    this.#ws.send(payload);
  }

  async #ensureToken() {
    if (this.#token && this.#expiresAt && this.#expiresAt > Date.now() + 10_000) {
      return;
    }
    const response = await fetch(`${this.#apiBaseUrl}/admin/tenants/${this.#tenantId}/embed_token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ locale: this.#locale, identity: this.#identity ?? null })
    });
    if (!response.ok) {
      throw new Error("token_fetch_failed");
    }
    const data = (await response.json()) as TokenResponse;
    this.#token = data.token;
    this.#expiresAt = Date.parse(data.expires_at);
  }

  #connect() {
    if (!this.#token) {
      return;
    }
    const url = new URL(`${this.#gatewayUrl}/widget`);
    url.searchParams.set("tenant_id", this.#tenantId);
    url.searchParams.set("token", this.#token);
    if (this.#identity?.userId) {
      url.searchParams.set("user_id", this.#identity.userId);
    }
    const ws = new WebSocket(url.toString());
    this.#ws = ws;

    ws.onopen = () => {
      this.#attempt = 0;
      this.#callbacks.onOpen();
      this.#flushQueue();
    };

    ws.onmessage = (event) => {
      this.#callbacks.onMessage(event.data);
    };

    ws.onerror = () => {
      this.#callbacks.onError(new Error("gateway_error"));
    };

    ws.onclose = async () => {
      this.#callbacks.onClose();
      if (this.#closed) {
        return;
      }
      this.#attempt += 1;
      const delay = Math.min(30_000, 2 ** this.#attempt * 1000);
      setTimeout(async () => {
        try {
          await this.#ensureToken();
          this.#connect();
        } catch (error) {
          this.#callbacks.onError(error instanceof Error ? error : new Error("reconnect_failed"));
          this.#connect();
        }
      }, delay);
    };
  }

  #flushQueue() {
    if (!this.#ws || this.#ws.readyState !== WebSocket.OPEN) {
      return;
    }
    while (this.#queue.length) {
      const chunk = this.#queue.shift();
      if (chunk) {
        this.#ws.send(chunk);
      }
    }
  }
}
