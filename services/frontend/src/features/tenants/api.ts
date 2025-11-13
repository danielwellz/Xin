import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { apiClient } from "@/api/httpClient";
import { AuditLogEntrySchema, ChannelSchema, TenantSchema } from "@/api/schemas";

const TenantsResponseSchema = z.array(TenantSchema);
const AuditResponseSchema = z.array(AuditLogEntrySchema);
const ChannelResponseSchema = z.array(ChannelSchema);

export const tenantQueryKeys = {
  tenants: ["tenants"] as const,
  audit: (tenantId: string | null) => ["audit", tenantId] as const,
  channels: (tenantId: string | null) => ["channels", tenantId] as const
};

export async function fetchTenants() {
  const { data } = await apiClient.get("/admin/tenants");
  return TenantsResponseSchema.parse(data);
}

export function useTenants() {
  return useQuery({
    queryKey: tenantQueryKeys.tenants,
    queryFn: fetchTenants,
    staleTime: 30_000
  });
}

export function useUpdateTenant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      tenantId,
      payload
    }: {
      tenantId: string;
      payload: { name?: string; timezone?: string; metadata?: Record<string, unknown> | null };
    }) => {
      const { data } = await apiClient.patch(`/admin/tenants/${tenantId}`, payload);
      return TenantSchema.parse(data);
    },
    onSuccess: (_, { tenantId }) => {
      queryClient.invalidateQueries({ queryKey: tenantQueryKeys.tenants });
      queryClient.invalidateQueries({ queryKey: tenantQueryKeys.audit(tenantId) });
    }
  });
}

export function useAuditLog(tenantId: string | null) {
  return useQuery({
    queryKey: tenantQueryKeys.audit(tenantId),
    queryFn: async () => {
      const { data } = await apiClient.get("/admin/audit", {
        params: { tenant_id: tenantId ?? undefined, limit: 50 }
      });
      return AuditResponseSchema.parse(data);
    },
    enabled: Boolean(tenantId)
  });
}

export function useChannels(tenantId: string | null) {
  return useQuery({
    queryKey: tenantQueryKeys.channels(tenantId),
    queryFn: async () => {
      if (!tenantId) {
        return [];
      }
      try {
        const { data } = await apiClient.get(`/admin/tenants/${tenantId}/channels`);
        return ChannelResponseSchema.parse(data);
      } catch (error: unknown) {
        console.warn("Channel list not yet available, returning empty list", error);
        return [];
      }
    },
    enabled: Boolean(tenantId)
  });
}
