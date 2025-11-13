import { useEffect } from "react";
import { useTranslation } from "react-i18next";

import { ChannelOverview } from "@/features/channels/ChannelOverview";
import { AuditTrail } from "@/features/audit/AuditTrail";

import { useTenants } from "./api";
import { TenantPicker } from "./TenantPicker";
import { TenantInlineEditor } from "./TenantInlineEditor";
import { useTenantContext } from "./TenantContext";

export function TenantManagementPage() {
  const { data: tenants = [], isLoading } = useTenants();
  const { selectedTenantId, setSelectedTenantId } = useTenantContext();
  const activeTenant = tenants.find((tenant) => tenant.id === selectedTenantId) ?? tenants[0];
  const { t } = useTranslation();

  useEffect(() => {
    if (!selectedTenantId && tenants.length > 0) {
      setSelectedTenantId(tenants[0].id);
    }
  }, [selectedTenantId, setSelectedTenantId, tenants]);

  if (isLoading) {
    return <p className="p-6 text-sm text-slate-500">Loading tenants…</p>;
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      <aside className="card max-h-[80vh] overflow-hidden">
        <h2 className="text-xl font-semibold">{t("tenant.listTitle")}</h2>
        <TenantPicker />
      </aside>
      <section className="space-y-6">
        {activeTenant ? <TenantInlineEditor tenant={activeTenant} /> : null}
        <ChannelOverview />
        <AuditTrail />
      </section>
    </div>
  );
}
