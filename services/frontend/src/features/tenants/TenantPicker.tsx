import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { useTenants } from "./api";
import { useTenantContext } from "./TenantContext";

export function TenantPicker() {
  const { data: tenants = [] } = useTenants();
  const { selectedTenantId, setSelectedTenantId } = useTenantContext();
  const { t } = useTranslation();
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search) {
      return tenants;
    }
    return tenants.filter((tenant) => {
      const haystack = `${tenant.name} ${tenant.metadata ? JSON.stringify(tenant.metadata) : ""}`.toLowerCase();
      return haystack.includes(search.toLowerCase());
    });
  }, [search, tenants]);

  return (
    <div className="space-y-3">
      <input
        type="search"
        placeholder={t("tenant.searchPlaceholder")}
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        className="w-full rounded-xl border border-border bg-white px-3 py-2 text-sm focus:border-brand focus:ring-2 focus:ring-brand/40"
      />
      <div className="max-h-80 space-y-2 overflow-y-auto">
        {filtered.map((tenant) => (
          <button
            key={tenant.id}
            type="button"
            onClick={() => setSelectedTenantId(tenant.id)}
            className={`flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left transition ${
              tenant.id === selectedTenantId ? "border-brand bg-brand/5" : "border-border hover:border-brand/60"
            }`}
          >
            <div>
              <p className="text-sm font-semibold">{tenant.name}</p>
              <p className="text-xs text-slate-500">{tenant.timezone}</p>
            </div>
            {tenant.id === selectedTenantId ? (
              <span className="chip bg-brand text-white">{t("tenant.inlineEdit")}</span>
            ) : null}
          </button>
        ))}
        {filtered.length === 0 ? (
          <p className="text-center text-sm text-slate-500">{t("tenant.empty")}</p>
        ) : null}
      </div>
    </div>
  );
}
