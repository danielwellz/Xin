import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ScopeGuard } from "@/features/auth/useScope";
import { useTenantContext } from "@/features/tenants/TenantContext";

import { useAutomationJobs, useAutomationRuleMutations, useAutomationRules } from "./api";

const defaultRule = {
  tenant_id: "",
  brand_id: "",
  name: "Follow-up reminder",
  trigger_type: "event",
  trigger_event: "conversation.idle",
  schedule_expression: "0 */2 * * *",
  condition: { field: "tags", op: "contains", value: "priority" },
  action_type: "webhook",
  action_payload: { url: "https://hooks.example.com/xin" },
  throttle_seconds: 300,
  max_retries: 3,
  is_active: true
};

export function AutomationBuilder() {
  const { selectedTenantId } = useTenantContext();
  const { data: rules = [] } = useAutomationRules(selectedTenantId);
  const { data: jobs = [] } = useAutomationJobs(selectedTenantId);
  const mutations = useAutomationRuleMutations(selectedTenantId);
  const { t } = useTranslation();
  const [ruleDraft, setRuleDraft] = useState(defaultRule);
  const [samplePayload, setSamplePayload] = useState(JSON.stringify({ conversation_id: "demo" }, null, 2));

  const handleDraftChange = (key: string, value: unknown) => {
    setRuleDraft((prev) => ({
      ...prev,
      [key]: value
    }));
  };

  const handleCreate = () => {
    if (!selectedTenantId) {
      return;
    }
    mutations.createRule.mutate({
      ...ruleDraft,
      tenant_id: selectedTenantId
    });
  };

  const handleTest = () => {
    if (!selectedTenantId) {
      return;
    }
    let payload: Record<string, unknown> = {};
    try {
      payload = JSON.parse(samplePayload);
    } catch {
      return;
    }
    mutations.testRule.mutate({
      rule: {
        ...ruleDraft,
        tenant_id: selectedTenantId
      },
      sample_payload: payload
    });
  };

  return (
    <ScopeGuard allow="platform_admin">
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card space-y-4">
          <h3 className="text-lg font-semibold">{t("automation.ruleDesigner")}</h3>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="text-sm font-medium text-slate-600">
              Name
              <input
                className="mt-1 w-full rounded-xl border border-border px-3 py-2 text-sm"
                value={ruleDraft.name}
                onChange={(event) => handleDraftChange("name", event.target.value)}
              />
            </label>
            <label className="text-sm font-medium text-slate-600">
              Trigger event
              <input
                className="mt-1 w-full rounded-xl border border-border px-3 py-2 text-sm"
                value={ruleDraft.trigger_event}
                onChange={(event) => handleDraftChange("trigger_event", event.target.value)}
              />
            </label>
          </div>
          <label className="text-sm font-medium text-slate-600">
            Condition JSON
            <textarea
              className="mt-1 h-32 w-full rounded-xl border border-border px-3 py-2 text-sm"
              value={JSON.stringify(ruleDraft.condition, null, 2)}
              onChange={(event) => {
                try {
                  handleDraftChange("condition", JSON.parse(event.target.value));
                } catch {
                  // ignore parse errors until valid JSON
                }
              }}
            />
          </label>
          <label className="text-sm font-medium text-slate-600">
            Action payload
            <textarea
              className="mt-1 h-32 w-full rounded-xl border border-border px-3 py-2 text-sm"
              value={JSON.stringify(ruleDraft.action_payload, null, 2)}
              onChange={(event) => {
                try {
                  handleDraftChange("action_payload", JSON.parse(event.target.value));
                } catch {
                  // no-op
                }
              }}
            />
          </label>
          <label className="text-sm font-medium text-slate-600">
            Sample payload
            <textarea
              className="mt-1 h-32 w-full rounded-xl border border-border px-3 py-2 text-sm"
              value={samplePayload}
              onChange={(event) => setSamplePayload(event.target.value)}
            />
          </label>
          <div className="flex gap-3">
            <button
              type="button"
              className="rounded-xl border border-brand px-4 py-2 text-sm font-semibold text-brand"
              onClick={handleTest}
            >
              {t("actions.test")}
            </button>
            <button
              type="button"
              className="rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-white"
              onClick={handleCreate}
            >
              {t("actions.save")}
            </button>
          </div>
          <section>
            <h4 className="text-sm font-semibold uppercase text-slate-400">{t("automation.jsonPreview")}</h4>
            <pre className="mt-2 max-h-64 overflow-auto rounded-xl bg-slate-900/90 p-4 text-xs text-emerald-100">
              {JSON.stringify(
                {
                  ...ruleDraft,
                  sample_payload: (() => {
                    try {
                      return JSON.parse(samplePayload);
                    } catch {
                      return { error: "invalid sample payload" };
                    }
                  })()
                },
                null,
                2
              )}
            </pre>
          </section>
        </div>
        <div className="space-y-4">
          <div className="card space-y-3">
            <h3 className="text-lg font-semibold">{t("automation.jobs")}</h3>
            <div className="space-y-2">
              {jobs.map((job) => (
                <div key={job.id} className="rounded-xl border border-border px-3 py-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{job.status}</span>
                    <span className="text-xs text-slate-500">{job.created_at}</span>
                  </div>
                  <p className="text-xs text-slate-500">Attempts: {job.attempts}</p>
                </div>
              ))}
              {jobs.length === 0 ? <p className="text-xs text-slate-500">No jobs yet.</p> : null}
            </div>
          </div>
          <div className="card space-y-3">
            <h3 className="text-lg font-semibold">{t("automation.title")}</h3>
            <div className="space-y-2">
              {rules.map((rule) => (
                <div key={rule.id} className="rounded-xl border border-border px-3 py-2 text-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold">{rule.name}</p>
                      <p className="text-xs text-slate-500">{rule.trigger_event}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => mutations.toggleRule.mutate({ ruleId: rule.id, action: rule.is_active ? "pause" : "resume" })}
                      className="text-xs font-semibold text-brand"
                    >
                      {rule.is_active ? t("automation.pause") : t("automation.resume")}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </ScopeGuard>
  );
}
