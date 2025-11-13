import DiffViewer from "react-diff-viewer-continued";
import Editor from "@monaco-editor/react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { ScopeGuard } from "@/features/auth/useScope";
import { useTenantContext } from "@/features/tenants/TenantContext";

import { useCreateDraft, usePolicies, usePolicyDiff, usePublishPolicy, useRetrievalDiagnostics } from "./api";

const schemaFields = [
  { key: "greeting", label: "Greeting prompt", helper: "Used for welcome messages." },
  { key: "safety", label: "Safety guardrails", helper: "Array of guardrail statements." },
  { key: "fallback", label: "Fallback response", helper: "Plain text fallback copy." }
] as const;

export function PolicyEditor() {
  const { selectedTenantId } = useTenantContext();
  const { data: policies = [] } = usePolicies(selectedTenantId);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const diffQuery = usePolicyDiff(selectedTenantId, selectedVersion);
  const createDraft = useCreateDraft();
  const publishPolicy = usePublishPolicy();
  const diagnostics = useRetrievalDiagnostics();
  const { t } = useTranslation();

  const [policyJson, setPolicyJson] = useState<Record<string, unknown>>({
    greeting: "Welcome to Xin Operator Console!",
    safety: ["Never share secrets", "Escalate billing questions"],
    fallback: "I could not resolve that just yet."
  });
  const [testPrompt, setTestPrompt] = useState("");
  const [brandId, setBrandId] = useState("");

  const draftVersion = useMemo(() => policies.find((item) => item.status === "draft"), [policies]);
  const publishedVersion = useMemo(() => policies.find((item) => item.status === "published"), [policies]);

  const handleSchemaSubmit = async () => {
    if (!selectedTenantId) {
      return;
    }
    await createDraft.mutateAsync({
      tenantId: selectedTenantId,
      policy: policyJson,
      summary: "Updated via UI schema form"
    });
  };

  const handlePublish = async () => {
    if (!selectedTenantId || !draftVersion) {
      return;
    }
    await publishPolicy.mutateAsync({ tenantId: selectedTenantId, versionId: draftVersion.id });
  };

  const handleDiagnostics = async () => {
    if (!selectedTenantId || !brandId || !testPrompt) {
      return;
    }
    await diagnostics.mutateAsync({
      tenantId: selectedTenantId,
      brandId,
      message: testPrompt
    });
  };

  return (
    <ScopeGuard allow={["platform_admin", "tenant_operator"]}>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card space-y-4">
          <h3 className="text-lg font-semibold">{t("policy.schemaForm")}</h3>
          <div className="space-y-4">
            {schemaFields.map((field) => (
              <label key={field.key} className="block text-sm font-medium text-slate-600">
                {field.label}
                <textarea
                  className="mt-1 w-full rounded-xl border border-border bg-slate-50 px-3 py-2 text-sm"
                  value={(policyJson[field.key] as string) ?? ""}
                  onChange={(event) =>
                    setPolicyJson((prev) => ({
                      ...prev,
                      [field.key]: event.target.value
                    }))
                  }
                />
                <span className="text-xs text-slate-400">{field.helper}</span>
              </label>
            ))}
          </div>
          <button
            type="button"
            onClick={handleSchemaSubmit}
            className="rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-white"
          >
            {t("actions.save")}
          </button>
          <section className="space-y-2">
            <h4 className="text-sm font-semibold uppercase text-slate-400">{t("policy.jsonEditor")}</h4>
            <div className="h-64 rounded-xl border border-border">
              <Editor
                defaultLanguage="json"
                value={JSON.stringify(policyJson, null, 2)}
                onChange={(value) => {
                  if (!value) {
                    return;
                  }
                  try {
                    setPolicyJson(JSON.parse(value));
                  } catch {
                    // no-op
                  }
                }}
                options={{ minimap: { enabled: false } }}
              />
            </div>
          </section>
          <section className="space-y-3">
            <h4 className="text-sm font-semibold uppercase text-slate-400">{t("policy.runPrompt")}</h4>
            <div className="grid gap-3 md:grid-cols-2">
              <input
                placeholder="Brand ID"
                className="rounded-xl border border-border px-3 py-2 text-sm"
                value={brandId}
                onChange={(event) => setBrandId(event.target.value)}
              />
              <input
                placeholder="Test prompt"
                className="rounded-xl border border-border px-3 py-2 text-sm"
                value={testPrompt}
                onChange={(event) => setTestPrompt(event.target.value)}
              />
            </div>
            <button
              type="button"
              onClick={handleDiagnostics}
              className="rounded-xl border border-brand px-4 py-2 text-sm font-semibold text-brand"
            >
              {t("actions.test")}
            </button>
            {diagnostics.data ? (
              <pre className="max-h-48 overflow-auto rounded-xl bg-slate-900/90 p-4 text-xs text-white">
                {JSON.stringify(diagnostics.data, null, 2)}
              </pre>
            ) : null}
          </section>
        </div>
        <div className="space-y-4">
          <div className="card space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">{t("policy.diff")}</h3>
                <p className="text-sm text-slate-500">{t("policy.publish")}</p>
              </div>
              <button
                type="button"
                className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                onClick={handlePublish}
                disabled={!draftVersion}
              >
                {t("actions.publish")}
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {policies.map((policy) => (
                <button
                  key={policy.id}
                  type="button"
                  onClick={() => setSelectedVersion(policy.version)}
                  className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                    selectedVersion === policy.version ? "border-brand text-brand" : "border-border"
                  }`}
                >
                  v{policy.version} · {policy.status}
                </button>
              ))}
            </div>
            {diffQuery.data ? (
              <DiffViewer
                oldValue={JSON.stringify({ previous: diffQuery.data.previous_version }, null, 2)}
                newValue={JSON.stringify(diffQuery.data.diff_json ?? {}, null, 2)}
                splitView
              />
            ) : (
              <p className="text-sm text-slate-500">Select a version to view differences.</p>
            )}
          </div>
          <div className="card space-y-3">
            <h3 className="text-lg font-semibold">{t("policy.diagnostics")}</h3>
            {diagnostics.isPending ? <p className="text-sm text-slate-500">Running diagnostics…</p> : null}
            {diagnostics.error ? (
              <p className="text-sm text-red-600">Diagnostics failed. Check tenant scopes.</p>
            ) : null}
          </div>
        </div>
      </div>
    </ScopeGuard>
  );
}
