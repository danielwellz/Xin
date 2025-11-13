import { Navigate, Route, Routes } from "react-router-dom";

import { AutomationBuilder } from "@/features/automation/AutomationBuilder";
import { ChannelWizard } from "@/features/channels/ChannelWizard";
import { KnowledgeBoard } from "@/features/knowledge/KnowledgeBoard";
import { ObservabilityPanel } from "@/features/observability/ObservabilityPanel";
import { PolicyEditor } from "@/features/policies/PolicyEditor";
import { TenantManagementPage } from "@/features/tenants/TenantManagementPage";

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/tenants" replace />} />
      <Route path="/tenants" element={<TenantManagementPage />} />
      <Route path="/channels/wizard" element={<ChannelWizard />} />
      <Route path="/policies" element={<PolicyEditor />} />
      <Route path="/knowledge" element={<KnowledgeBoard />} />
      <Route path="/automation" element={<AutomationBuilder />} />
      <Route path="/observability" element={<ObservabilityPanel />} />
    </Routes>
  );
}
