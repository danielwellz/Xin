import { z } from "zod";

export const ChannelTypeSchema = z.enum(["instagram", "telegram", "whatsapp", "web"]);
export type ChannelType = z.infer<typeof ChannelTypeSchema>;

export const TenantSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  timezone: z.string(),
  metadata: z.record(z.any()).nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
  embed_config: z
    .object({
      tenant_id: z.string().uuid(),
      handshake_salt: z.string(),
      token_ttl_seconds: z.number(),
      theme: z.record(z.any()).nullable().optional(),
      widget_options: z.record(z.any()).nullable().optional()
    })
    .nullable()
    .optional()
});
export type Tenant = z.infer<typeof TenantSchema>;

export const ChannelSchema = z.object({
  id: z.string().uuid(),
  brand_id: z.string().uuid(),
  channel_type: ChannelTypeSchema,
  display_name: z.string(),
  is_active: z.boolean(),
  credentials: z.record(z.any()).nullable().optional(),
  hmac_secret: z.string().nullable().optional()
});
export type Channel = z.infer<typeof ChannelSchema>;

export const PolicyVersionSchema = z.object({
  id: z.string().uuid(),
  version: z.number(),
  status: z.string(),
  summary: z.string().nullable(),
  created_at: z.string(),
  published_at: z.string().nullable()
});
export type PolicyVersion = z.infer<typeof PolicyVersionSchema>;

export const PolicyDiffSchema = z.object({
  version: z.number(),
  previous_version: z.number().nullable(),
  diff_json: z.record(z.any()),
  created_at: z.string(),
  created_by: z.string(),
  notes: z.string().nullable()
});

export const RetrievalConfigSchema = z.object({
  tenant_id: z.string().uuid(),
  hybrid_weight: z.number(),
  min_score: z.number(),
  max_documents: z.number(),
  context_budget_tokens: z.number(),
  filters: z.record(z.any()).nullable(),
  fallback_llm: z.string().nullable(),
  updated_at: z.string()
});
export type RetrievalConfig = z.infer<typeof RetrievalConfigSchema>;

export const KnowledgeAssetSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  brand_id: z.string().uuid(),
  knowledge_source_id: z.string().uuid(),
  title: z.string(),
  tags: z.array(z.string()).nullable(),
  visibility: z.string(),
  status: z.string(),
  created_at: z.string(),
  updated_at: z.string()
});
export type KnowledgeAsset = z.infer<typeof KnowledgeAssetSchema>;

export const IngestionJobSchema = z.object({
  id: z.string().uuid(),
  knowledge_source_id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  brand_id: z.string().uuid(),
  status: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  cancelled_at: z.string().nullable().optional(),
  total_chunks: z.number().nullable(),
  processed_chunks: z.number().nullable(),
  failure_reason: z.string().nullable(),
  logs: z.array(z.object({ level: z.string(), message: z.string(), ts: z.string() })).nullable()
});
export type IngestionJob = z.infer<typeof IngestionJobSchema>;

export const AutomationRuleSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  brand_id: z.string().uuid(),
  name: z.string(),
  trigger_type: z.string(),
  trigger_event: z.string(),
  schedule_expression: z.string().nullable(),
  condition: z.record(z.any()).nullable(),
  action_type: z.string(),
  action_payload: z.record(z.any()),
  throttle_seconds: z.number(),
  max_retries: z.number(),
  is_active: z.boolean(),
  last_run_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string()
});
export type AutomationRule = z.infer<typeof AutomationRuleSchema>;

export const AutomationJobSchema = z.object({
  id: z.string().uuid(),
  rule_id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  brand_id: z.string().uuid(),
  status: z.string(),
  attempts: z.number(),
  scheduled_for: z.string().nullable(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  payload: z.record(z.any()),
  failure_reason: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string()
});
export type AutomationJob = z.infer<typeof AutomationJobSchema>;

export const AuditLogEntrySchema = z.object({
  id: z.string().uuid(),
  created_at: z.string(),
  tenant_id: z.string().uuid().nullable(),
  actor: z.string(),
  action: z.string(),
  target_type: z.string(),
  target_id: z.string(),
  metadata: z.record(z.any()).nullable()
});
export type AuditLogEntry = z.infer<typeof AuditLogEntrySchema>;

export const DiagnosticsResponseSchema = z.object({
  query: z.string(),
  documents: z.array(z.record(z.any())),
  applied_config: RetrievalConfigSchema
});
export type DiagnosticsResponse = z.infer<typeof DiagnosticsResponseSchema>;

export const MetricSampleSchema = z.object({
  name: z.string(),
  value: z.number(),
  unit: z.string().optional(),
  ts: z.string()
});
export type MetricSample = z.infer<typeof MetricSampleSchema>;
