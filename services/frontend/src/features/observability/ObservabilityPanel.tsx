import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { apiClient } from "@/api/httpClient";
import { ScopeGuard } from "@/features/auth/useScope";
import { parsePrometheusMetrics } from "@/lib/prometheus";

const METRICS = ["automation_queue_depth", "ingestion_jobs_inflight", "http_request_latency_seconds_sum"];

export function ObservabilityPanel() {
  const { t } = useTranslation();
  const grafanaUrl = import.meta.env.VITE_GRAFANA_SNAPSHOT_URL as string | undefined;
  const { data } = useQuery({
    queryKey: ["observability", "metrics"],
    queryFn: async () => {
      const response = await apiClient.get("/metrics", { responseType: "text" });
      return response.data as string;
    },
    refetchInterval: 15000
  });

  const metrics = data ? parsePrometheusMetrics(data, METRICS) : {};

  return (
    <ScopeGuard allow={["platform_admin", "tenant_operator"]}>
    <div className="card space-y-4">
      <h3 className="text-lg font-semibold">{t("observability.title")}</h3>
      <dl className="grid gap-4 sm:grid-cols-3">
        <MetricTile label={t("observability.queueDepth")} value={metrics.automation_queue_depth} unit="jobs" />
        <MetricTile label={t("observability.ingestionLag")} value={metrics.ingestion_jobs_inflight} unit="inflight" />
        <MetricTile
          label={t("observability.latency")}
          value={metrics.http_request_latency_seconds_sum ? metrics.http_request_latency_seconds_sum * 1000 : undefined}
          unit="ms"
        />
      </dl>
      {grafanaUrl ? (
        <div>
          <p className="text-sm font-semibold text-slate-500">{t("observability.grafana")}</p>
          <iframe title="Grafana" src={grafanaUrl} className="mt-2 h-64 w-full rounded-xl border border-border" />
        </div>
      ) : (
        <p className="text-sm text-slate-500">
          Provide `VITE_GRAFANA_SNAPSHOT_URL` to embed the production panel from docs/RUNBOOK.md §6.
        </p>
      )}
    </div>
    </ScopeGuard>
  );
}

function MetricTile({ label, value, unit }: { label: string; value?: number; unit: string }) {
  return (
    <div className="rounded-2xl border border-border bg-slate-50/60 p-4">
      <dt className="text-xs uppercase text-slate-400">{label}</dt>
      <dd className="text-2xl font-semibold text-slate-900">
        {value ?? "—"} <span className="text-sm text-slate-500">{unit}</span>
      </dd>
    </div>
  );
}
