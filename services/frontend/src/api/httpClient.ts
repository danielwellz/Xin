import axios from "axios";
import { v4 as uuid } from "uuid";

type ContextGetters = {
  getToken: () => string | null;
  getTenantId: () => string | null;
};

let contextGetters: ContextGetters = {
  getToken: () => null,
  getTenantId: () => null
};

function resolveDefaultBaseUrl(): string {
  if (typeof window !== "undefined" && window.location?.origin) {
    return window.location.origin;
  }
  return __API_BASE_URL__;
}

export const apiClient = axios.create({
  baseURL:
    (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? resolveDefaultBaseUrl(),
  timeout: 15000
});

export function registerHttpContext(getters: Partial<ContextGetters>) {
  contextGetters = {
    ...contextGetters,
    ...getters
  };
}

apiClient.interceptors.request.use((config) => {
  const token = contextGetters.getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const tenantId = contextGetters.getTenantId();
  if (tenantId) {
    config.headers["X-Tenant-ID"] = tenantId;
  }
  config.headers["X-Trace-Id"] = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : uuid();
  config.headers["X-Requested-With"] = "Xin-Operator-Console";
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.dispatchEvent(new CustomEvent("xin:auth:expired"));
    }
    return Promise.reject(error);
  }
);

if (import.meta.env.VITE_USE_MOCKS === "true") {
  void import("../mocks/mockApi").then(({ registerMockApi }) => registerMockApi(apiClient));
}
