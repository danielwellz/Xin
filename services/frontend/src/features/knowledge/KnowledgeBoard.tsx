import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ScopeGuard } from "@/features/auth/useScope";
import { useTenantContext } from "@/features/tenants/TenantContext";

import { useIngestionJobs, useKnowledgeAssets, useRetryIngestionJob, useUploadAsset } from "./api";

export function KnowledgeBoard() {
  const { selectedTenantId } = useTenantContext();
  const { data: assets = [] } = useKnowledgeAssets(selectedTenantId);
  const { data: jobs = [] } = useIngestionJobs(selectedTenantId);
  const retryJob = useRetryIngestionJob(selectedTenantId);
  const uploadAsset = useUploadAsset(selectedTenantId);
  const { t } = useTranslation();
  const [progress, setProgress] = useState<number>(0);
  const [file, setFile] = useState<File | null>(null);
  const [brandId, setBrandId] = useState("");

  const handleUpload = () => {
    if (!file || !brandId) {
      return;
    }
    uploadAsset.mutate({
      file,
      visibility: "private",
      brandId,
      onProgress: setProgress
    });
  };

  return (
    <ScopeGuard allow={["platform_admin", "tenant_operator"]}>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">{t("knowledge.assets")}</h3>
            <label className="rounded-xl border border-dashed border-border px-4 py-2 text-sm font-semibold text-slate-600">
              {t("upload.selectFile")}
              <input type="file" className="hidden" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
            </label>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <input
              type="text"
              placeholder="Brand UUID"
              value={brandId}
              onChange={(event) => setBrandId(event.target.value)}
              className="rounded-xl border border-border px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={handleUpload}
              className="rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
              disabled={!file || !brandId}
            >
              {t("actions.upload")}
            </button>
          </div>
          {progress > 0 ? (
            <div className="rounded-full bg-slate-200">
              <div className="rounded-full bg-brand px-2 py-1 text-xs text-white" style={{ width: `${progress}%` }}>
                {progress}%
              </div>
            </div>
          ) : null}
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-slate-400">
                <th>{t("knowledge.assets")}</th>
                <th>{t("knowledge.progress")}</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((asset) => (
                <tr key={asset.id} className="border-b border-slate-100">
                  <td className="py-2 font-medium">{asset.title}</td>
                  <td className="py-2 text-xs text-slate-500">{asset.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card space-y-4">
          <h3 className="text-lg font-semibold">{t("knowledge.jobs")}</h3>
          <div className="max-h-80 overflow-auto">
            {jobs.map((job) => (
              <div key={job.id} className="mb-3 rounded-xl border border-border p-3 text-sm">
                <div className="flex items-center justify-between">
                  <p className="font-semibold">{job.status}</p>
                  <button
                    type="button"
                    className="text-xs font-semibold text-brand"
                    onClick={() => retryJob.mutate({ jobId: job.id })}
                  >
                    {t("knowledge.retry")}
                  </button>
                </div>
                <p className="text-xs text-slate-500">
                  {job.processed_chunks ?? 0}/{job.total_chunks ?? 0} chunks
                </p>
                {job.logs ? (
                  <details className="mt-2 rounded-lg bg-slate-50 p-2">
                    <summary className="cursor-pointer text-xs font-semibold">{t("knowledge.logs")}</summary>
                    <pre className="mt-2 whitespace-pre-wrap text-xs">{JSON.stringify(job.logs, null, 2)}</pre>
                  </details>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      </div>
    </ScopeGuard>
  );
}
