import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from "axios";
import { v4 as uuid } from "uuid";

type MockState = {
  tenants: any[];
  policies: any[];
  audit: any[];
  assets: any[];
  jobs: any[];
  automationRules: any[];
  automationJobs: any[];
};

const tenantId = "11111111-1111-1111-1111-111111111111";
const brandId = "22222222-2222-2222-2222-222222222222";

const state: MockState = {
  tenants: [
    {
      id: tenantId,
      name: "Acme Support",
      timezone: "UTC",
      metadata: { plan: "enterprise" },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      embed_config: null
    }
  ],
  policies: [
    {
      id: uuid(),
      version: 1,
      status: "published",
      summary: "Base",
      created_at: new Date().toISOString(),
      published_at: new Date().toISOString()
    }
  ],
  audit: [
    {
      id: uuid(),
      created_at: new Date().toISOString(),
      tenant_id: tenantId,
      actor: "system",
      action: "tenant.updated",
      target_type: "tenant",
      target_id: tenantId,
      metadata: { field: "timezone", value: "UTC" }
    }
  ],
  assets: [
    {
      id: uuid(),
      tenant_id: tenantId,
      brand_id: brandId,
      knowledge_source_id: uuid(),
      title: "FAQ pack",
      tags: ["faq"],
      visibility: "private",
      status: "ready",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
  ],
  jobs: [
    {
      id: uuid(),
      knowledge_source_id: uuid(),
      tenant_id: tenantId,
      brand_id: brandId,
      status: "completed",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      total_chunks: 20,
      processed_chunks: 20,
      failure_reason: null,
      logs: [{ level: "info", message: "chunked", ts: new Date().toISOString() }]
    }
  ],
  automationRules: [
    {
      id: uuid(),
      tenant_id: tenantId,
      brand_id: brandId,
      name: "Escalate VIP",
      trigger_type: "event",
      trigger_event: "conversation.created",
      schedule_expression: null,
      condition: { field: "tags", op: "contains", value: "vip" },
      action_type: "webhook",
      action_payload: { url: "https://hooks" },
      throttle_seconds: 300,
      max_retries: 3,
      is_active: true,
      last_run_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
  ],
  automationJobs: [
    {
      id: uuid(),
      rule_id: uuid(),
      tenant_id: tenantId,
      brand_id: brandId,
      status: "completed",
      attempts: 1,
      scheduled_for: null,
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      payload: { id: "demo" },
      failure_reason: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
  ]
};

function ok<T>(config: AxiosRequestConfig, data: T, status = 200): AxiosResponse<T> {
  return {
    data,
    status,
    statusText: "OK",
    headers: {},
    config
  };
}

function parseBody(config: AxiosRequestConfig) {
  if (!config.data) {
    return {};
  }
  if (typeof config.data === "string") {
    try {
      return JSON.parse(config.data);
    } catch {
      return {};
    }
  }
  return config.data;
}

async function resolve(config: AxiosRequestConfig) {
  const base = config.baseURL || window.location.origin;
  const url = new URL(config.url || "", base);
  const method = (config.method || "get").toUpperCase();
  const path = url.pathname;
  const body = parseBody(config);

  if (method === "GET" && path === "/admin/tenants") {
    return state.tenants;
  }
  if (method === "PATCH" && path.startsWith("/admin/tenants/")) {
    const id = path.split("/").at(-1);
    const tenant = state.tenants.find((item) => item.id === id);
    Object.assign(tenant, body, { updated_at: new Date().toISOString() });
    return tenant;
  }
  if (method === "GET" && path === "/admin/audit") {
    return state.audit;
  }
  if (method === "GET" && path === "/admin/knowledge_assets") {
    return state.assets;
  }
  if (method === "GET" && path === "/admin/ingestion_jobs") {
    return state.jobs;
  }
  if (method === "POST" && path.includes("/admin/ingestion_jobs") && path.endsWith("/retry")) {
    return state.jobs[0];
  }
  if (method === "POST" && path === "/admin/knowledge_assets/upload") {
    const asset = {
      id: uuid(),
      tenant_id: tenantId,
      brand_id: brandId,
      knowledge_source_id: uuid(),
      title: "Upload",
      tags: null,
      visibility: "private",
      status: "pending",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    state.assets.push(asset);
    return asset;
  }
  if (method === "GET" && path.startsWith("/admin/policies/") && !path.includes("/diff")) {
    return state.policies;
  }
  if (method === "POST" && path.includes("/draft")) {
    const draft = {
      id: uuid(),
      version: 2,
      status: "draft",
      summary: body.summary ?? "draft",
      created_at: new Date().toISOString(),
      published_at: null
    };
    state.policies.push(draft);
    return draft;
  }
  if (method === "POST" && path.includes("/publish")) {
    const latest = state.policies.at(-1);
    latest.status = "published";
    latest.published_at = new Date().toISOString();
    return latest;
  }
  if (method === "GET" && path.includes("/diff/")) {
    return {
      version: 2,
      previous_version: 1,
      diff_json: { greeting: "سلام" },
      created_at: new Date().toISOString(),
      created_by: "mock",
      notes: null
    };
  }
  if (method === "POST" && path === "/admin/diagnostics/retrieval") {
    return {
      query: body.message,
      documents: [{ id: "doc1", text: "Order policy", metadata: {} }],
      applied_config: {
        tenant_id: tenantId,
        hybrid_weight: 0.4,
        min_score: 0.3,
        max_documents: 5,
        context_budget_tokens: 1500,
        filters: null,
        fallback_llm: null,
        updated_at: new Date().toISOString()
      }
    };
  }
  if (path === "/admin/channels" && method === "POST") {
    return {
      id: uuid(),
      brand_id: brandId,
      channel_type: body.channel_type,
      display_name: body.display_name,
      is_active: true,
      credentials: body.credentials,
      hmac_secret: uuid()
    };
  }
  if (method === "GET" && path === "/admin/automation/rules") {
    return state.automationRules;
  }
  if (method === "GET" && path === "/admin/automation/jobs") {
    return state.automationJobs;
  }
  if (method === "POST" && path === "/admin/automation/rules") {
    const rule = { ...body, id: uuid(), created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
    state.automationRules.push(rule);
    return rule;
  }
  if (method === "POST" && path.includes("/automation/rules/") && path.endsWith("/pause")) {
    const id = path.split("/")[4];
    const rule = state.automationRules.find((item) => item.id === id);
    rule.is_active = false;
    return rule;
  }
  if (method === "POST" && path.includes("/automation/rules/") && path.endsWith("/resume")) {
    const id = path.split("/")[4];
    const rule = state.automationRules.find((item) => item.id === id);
    rule.is_active = true;
    return rule;
  }
  if (method === "POST" && path === "/admin/automation/test") {
    return { status: "ok" };
  }
  if (method === "GET" && path === "/metrics") {
    return `automation_queue_depth 3\ningestion_jobs_inflight 1\nhttp_request_latency_seconds_sum 0.23`;
  }
  throw new Error(`No mock for ${method} ${path}`);
}

export async function registerMockApi(instance: AxiosInstance) {
  instance.defaults.adapter = async (config) => {
    const data = await resolve(config);
    return ok(config, data);
  };
}
