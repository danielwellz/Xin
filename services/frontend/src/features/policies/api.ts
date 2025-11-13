import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { apiClient } from "@/api/httpClient";
import { DiagnosticsResponseSchema, PolicyDiffSchema, PolicyVersionSchema } from "@/api/schemas";

const PolicyListSchema = z.array(PolicyVersionSchema);

export const policyQueryKeys = {
  list: (tenantId: string | null) => ["policies", tenantId] as const,
  diff: (tenantId: string | null, version: number | null) => ["policies", tenantId, "diff", version] as const,
  diagnostics: (tenantId: string | null) => ["policies", tenantId, "diagnostics"] as const
};

export function usePolicies(tenantId: string | null) {
  return useQuery({
    queryKey: policyQueryKeys.list(tenantId),
    queryFn: async () => {
      if (!tenantId) {
        return [];
      }
      const { data } = await apiClient.get(`/admin/policies/${tenantId}`);
      return PolicyListSchema.parse(data);
    },
    enabled: Boolean(tenantId)
  });
}

export function usePolicyDiff(tenantId: string | null, version: number | null) {
  return useQuery({
    queryKey: policyQueryKeys.diff(tenantId, version),
    queryFn: async () => {
      if (!tenantId || !version) {
        return null;
      }
      const { data } = await apiClient.get(`/admin/policies/${tenantId}/diff/${version}`);
      return PolicyDiffSchema.parse(data);
    },
    enabled: Boolean(tenantId && version)
  });
}

export function useCreateDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      tenantId,
      policy,
      summary
    }: {
      tenantId: string;
      policy: Record<string, unknown>;
      summary?: string;
    }) => {
      const { data } = await apiClient.post(`/admin/policies/${tenantId}/draft`, {
        tenant_id: tenantId,
        policy_json: policy,
        summary: summary ?? "Updated via console"
      });
      return PolicyVersionSchema.parse(data);
    },
    onSuccess: (_, { tenantId }) => {
      queryClient.invalidateQueries({ queryKey: policyQueryKeys.list(tenantId) });
    }
  });
}

export function usePublishPolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ tenantId, versionId }: { tenantId: string; versionId: string }) => {
      const { data } = await apiClient.post(`/admin/policies/${tenantId}/publish`, {
        version_id: versionId
      });
      return PolicyVersionSchema.parse(data);
    },
    onSuccess: (_, { tenantId }) => {
      queryClient.invalidateQueries({ queryKey: policyQueryKeys.list(tenantId) });
    }
  });
}

export function useRetrievalDiagnostics() {
  return useMutation({
    mutationFn: async ({
      tenantId,
      brandId,
      message
    }: {
      tenantId: string;
      brandId: string;
      message: string;
      channelId?: string;
    }) => {
      const { data } = await apiClient.post("/admin/diagnostics/retrieval", {
        tenant_id: tenantId,
        brand_id: brandId,
        message
      });
      return DiagnosticsResponseSchema.parse(data);
    }
  });
}
