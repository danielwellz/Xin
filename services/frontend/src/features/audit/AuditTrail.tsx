import { useTranslation } from "react-i18next";

import { useAuditLog } from "@/features/tenants/api";
import { useTenantContext } from "@/features/tenants/TenantContext";

export function AuditTrail() {
  const { selectedTenantId } = useTenantContext();
  const { data: entries = [] } = useAuditLog(selectedTenantId);
  const { t } = useTranslation();

  return (
    <div className="card space-y-4">
      <h3 className="text-lg font-semibold">{t("tenant.audit")}</h3>
      <ul className="max-h-72 space-y-3 overflow-auto">
        {entries.map((entry) => (
          <li key={entry.id} className="rounded-xl border border-border px-3 py-2 text-sm">
            <div className="flex items-center justify-between">
              <p className="font-semibold">{entry.action}</p>
              <span className="text-xs text-slate-500">{new Date(entry.created_at).toLocaleString()}</span>
            </div>
            <p className="text-xs text-slate-500">{entry.actor}</p>
            {entry.metadata ? (
              <pre className="mt-2 max-h-32 overflow-auto rounded-lg bg-slate-50 p-2 text-xs">
                {JSON.stringify(entry.metadata, null, 2)}
              </pre>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
