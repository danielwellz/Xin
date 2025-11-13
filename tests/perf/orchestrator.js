import http from "k6/http";
import { check, group, sleep } from "k6";
import { Trend, Rate, Counter } from "k6/metrics";
import { uuidv4 } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";
import { hmac } from "k6/crypto";
import encoding from "k6/encoding";

const DEFAULT_WORKLOAD = {
  tenants: [
    {
      id: "11111111-1111-1111-1111-111111111111",
      brands: [
        {
          name: "alpha",
          brand_id: "22222222-2222-2222-2222-222222222222",
          channel_id: "33333333-3333-3333-3333-333333333333",
          channels: {
            webchat: 0.4,
            instagram: 0.25,
            telegram: 0.15,
            whatsapp: 0.1,
            automation: 0.1,
          },
        },
      ],
    },
  ],
  ingestion: { jobs_per_minute: 3, spike_multiplier: 2 },
  automation: { trigger_rate_per_minute: 5, webhook_ratio: 0.6, crm_ratio: 0.2, email_ratio: 0.2 },
};

const workload = loadWorkload();
const brandProfiles = flattenBrands(workload.tenants);

const config = {
  gatewayUrl: __ENV.GATEWAY_URL || "http://localhost:8080/webchat/webhook",
  orchestratorUrl: __ENV.ORCHESTRATOR_URL || "http://localhost:8000",
  adminToken: __ENV.ADMIN_TOKEN || "",
  webhookSecret: __ENV.WEBHOOK_SECRET || "dev-web",
  ingestionJobsPerMinute: workload.ingestion?.jobs_per_minute || 3,
  automationRate: workload.automation?.trigger_rate_per_minute || 5,
};

export const options = {
  vus: Number(__ENV.K6_VUS || 100),
  duration: __ENV.K6_DURATION || "10m",
  thresholds: {
    http_req_duration: ["p(95)<1500"],
    http_req_failed: ["rate<0.01"],
    gateway_latency: ["p(95)<1500"],
    orchestrator_latency: ["p(95)<1500"],
    automation_latency: ["p(95)<1500"],
  },
};

const gatewayLatency = new Trend("gateway_latency", true);
const orchestratorLatency = new Trend("orchestrator_latency", true);
const automationLatency = new Trend("automation_latency", true);
const perfErrors = new Rate("perf_errors");
const chaosCounter = new Counter("chaos_events_triggered");

export default function main() {
  const brand = pickBrand();
  const correlationId = uuidv4();

  group("gateway->orchestrator", () => {
    const payload = buildWebhookPayload(brand);
    const headers = webhookHeaders(payload, correlationId);
    const response = http.post(config.gatewayUrl, payload, {
      headers,
      tags: { channel: brand.selectedChannel },
    });
    const ok = check(response, {
      "gateway status 202": (r) => r.status === 202,
    });
    gatewayLatency.add(response.timings.duration);
    if (!ok) {
      perfErrors.add(1);
    }
  });

  if (shouldRunIngestion()) {
    group("ingestion job", () => {
      const response = uploadKnowledge(brand, correlationId);
      orchestratorLatency.add(response.timings.duration);
      const ok = check(response, { "ingestion accepted": (r) => r.status < 400 });
      if (!ok) {
        perfErrors.add(1);
      }
    });
  }

  if (shouldFireAutomation()) {
    group("automation trigger", () => {
      const response = triggerAutomation(brand, correlationId);
      automationLatency.add(response.timings.duration);
      const ok = check(response, { "automation 200": (r) => r.status === 200 });
      if (!ok) {
        perfErrors.add(1);
      }
    });
  }

  sleep(Math.random() * 1.5);
}

// Helpers ---------------------------------------------------------------

function loadWorkload() {
  if (__ENV.WORKLOAD_FILE) {
    try {
      const raw = open(__ENV.WORKLOAD_FILE);
      return JSON.parse(raw);
    } catch (err) {
      console.warn(`Failed to parse workload file: ${err}`);
    }
  }
  return DEFAULT_WORKLOAD;
}

function flattenBrands(tenants = []) {
  const output = [];
  tenants.forEach((tenant) => {
    (tenant.brands || []).forEach((brand) => {
      output.push({
        tenantId: tenant.id,
        brandId: brand.brand_id,
        channelId: brand.channel_id,
        name: brand.name,
        channelWeights: brand.channels || { webchat: 1 },
      });
    });
  });
  return output.length ? output : DEFAULT_WORKLOAD.tenants[0].brands;
}

function pickBrand() {
  const brand = brandProfiles[Math.floor(Math.random() * brandProfiles.length)];
  const selectedChannel = weightedChannel(brand.channelWeights);
  return { ...brand, selectedChannel };
}

function weightedChannel(weights) {
  const entries = Object.entries(weights || { webchat: 1 });
  const total = entries.reduce((acc, [, weight]) => acc + weight, 0);
  const target = Math.random() * total;
  let running = 0;
  for (const [channel, weight] of entries) {
    running += weight;
    if (target <= running) {
      return channel;
    }
  }
  return entries[0][0];
}

function buildWebhookPayload(brand) {
  const occurredAt = new Date().toISOString();
  return JSON.stringify({
    event_id: uuidv4(),
    tenant_id: brand.tenantId,
    brand_id: brand.brandId,
    channel_id: brand.channelId,
    sender_id: `perf-${uuidv4().slice(0, 8)}`,
    message: `Load test message for ${brand.name}`,
    locale: "en-US",
    metadata: { perf: true, channel: brand.selectedChannel },
    occurred_at: occurredAt,
  });
}

function webhookHeaders(body, correlationId) {
  const signature = hmac("sha256", config.webhookSecret, body, "hex");
  return {
    "Content-Type": "application/json",
    "X-Request-ID": correlationId,
    "X-Webchat-Signature": signature,
  };
}

function uploadKnowledge(brand, correlationId) {
  if (!config.adminToken) {
    return { status: 204, timings: { duration: 0 } };
  }
  const url = `${config.orchestratorUrl}/admin/knowledge_assets/upload`;
  const formPayload = {
    tenant_id: brand.tenantId,
    brand_id: brand.brandId,
    filename: `perf-${Date.now()}.md`,
    content: encoding.b64encode("# Perf doc\n\nThis seeds ingestion."),
  };
  return http.post(url, JSON.stringify(formPayload), {
    headers: {
      Authorization: `Bearer ${config.adminToken}`,
      "Content-Type": "application/json",
      "X-Request-ID": correlationId,
    },
    tags: { flow: "ingestion" },
  });
}

function triggerAutomation(brand, correlationId) {
  if (!config.adminToken) {
    return { status: 200, timings: { duration: 0 } };
  }
  const url = `${config.orchestratorUrl}/admin/automation/test`;
  const payload = {
    tenant_id: brand.tenantId,
    brand_id: brand.brandId,
    rule: {
      action_type: "webhook",
      action_payload: {
        url: "https://httpbin.org/post",
        method: "POST",
        body: { sample: "automation" },
      },
    },
  };
  return http.post(url, JSON.stringify(payload), {
    headers: {
      Authorization: `Bearer ${config.adminToken}`,
      "Content-Type": "application/json",
      "X-Request-ID": correlationId,
    },
    tags: { flow: "automation" },
  });
}

function shouldRunIngestion() {
  const jobsPerSec = config.ingestionJobsPerMinute / 60;
  return Math.random() < jobsPerSec / options.vus;
}

function shouldFireAutomation() {
  const triggersPerSec = config.automationRate / 60;
  return Math.random() < triggersPerSec / options.vus;
}

// Chaos helper (manual trigger during tests)
export function chaos(eventName) {
  chaosCounter.add(1, { event: eventName });
}
