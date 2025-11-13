import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { apiClient } from "@/api/httpClient";
import { AutomationJobSchema, AutomationRuleSchema } from "@/api/schemas";

const RuleListSchema = z.array(AutomationRuleSchema);
const JobListSchema = z.array(AutomationJobSchema);

export const automationQueryKeys = {
  rules: (tenantId: string | null) => ["automation", tenantId, "rules"] as const,
  jobs: (tenantId: string | null) => ["automation", tenantId, "jobs"] as const
};

export function useAutomationRules(tenantId: string | null) {
  return useQuery({
    queryKey: automationQueryKeys.rules(tenantId),
    queryFn: async () => {
      if (!tenantId) {
        return [];
      }
      const { data } = await apiClient.get("/admin/automation/rules", {
        params: { tenant_id: tenantId }
      });
      return RuleListSchema.parse(data);
    },
    enabled: Boolean(tenantId)
  });
}

export function useAutomationJobs(tenantId: string | null) {
  return useQuery({
    queryKey: automationQueryKeys.jobs(tenantId),
    queryFn: async () => {
      if (!tenantId) {
        return [];
      }
      const { data } = await apiClient.get("/admin/automation/jobs", {
        params: { tenant_id: tenantId }
      });
      return JobListSchema.parse(data);
    },
    enabled: Boolean(tenantId),
    refetchInterval: 10_000
  });
}

export function useAutomationRuleMutations(tenantId: string | null) {
  const queryClient = useQueryClient();
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: automationQueryKeys.rules(tenantId) });
    queryClient.invalidateQueries({ queryKey: automationQueryKeys.jobs(tenantId) });
  };

  const createRule = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await apiClient.post("/admin/automation/rules", payload);
      return AutomationRuleSchema.parse(data);
    },
    onSuccess: invalidate
  });

  const toggleRule = useMutation({
    mutationFn: async ({ ruleId, action }: { ruleId: string; action: "pause" | "resume" }) => {
      const { data } = await apiClient.post(`/admin/automation/rules/${ruleId}/${action}`);
      return AutomationRuleSchema.parse(data);
    },
    onSuccess: invalidate
  });

  const testRule = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await apiClient.post("/admin/automation/test", payload);
      return data;
    }
  });

  return { createRule, toggleRule, testRule };
}
