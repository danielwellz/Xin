import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Upload } from "tus-js-client";
import { z } from "zod";

import { apiClient } from "@/api/httpClient";
import { IngestionJobSchema, KnowledgeAssetSchema } from "@/api/schemas";

const AssetListSchema = z.array(KnowledgeAssetSchema);
const JobListSchema = z.array(IngestionJobSchema);

export const knowledgeQueryKeys = {
  assets: (tenantId: string | null) => ["knowledge", tenantId, "assets"] as const,
  jobs: (tenantId: string | null) => ["knowledge", tenantId, "jobs"] as const
};

export function useKnowledgeAssets(tenantId: string | null) {
  return useQuery({
    queryKey: knowledgeQueryKeys.assets(tenantId),
    queryFn: async () => {
      if (!tenantId) {
        return [];
      }
      const { data } = await apiClient.get("/admin/knowledge_assets", {
        params: { tenant_id: tenantId }
      });
      return AssetListSchema.parse(data);
    },
    enabled: Boolean(tenantId)
  });
}

export function useIngestionJobs(tenantId: string | null) {
  return useQuery({
    queryKey: knowledgeQueryKeys.jobs(tenantId),
    queryFn: async () => {
      if (!tenantId) {
        return [];
      }
      const { data } = await apiClient.get("/admin/ingestion_jobs", {
        params: { tenant_id: tenantId }
      });
      return JobListSchema.parse(data);
    },
    enabled: Boolean(tenantId),
    refetchInterval: 15_000
  });
}

export function useRetryIngestionJob(tenantId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ jobId, reason }: { jobId: string; reason?: string }) => {
      const { data } = await apiClient.post(`/admin/ingestion_jobs/${jobId}/retry`, {
        reason
      });
      return IngestionJobSchema.parse(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: knowledgeQueryKeys.jobs(tenantId) });
    }
  });
}

export function useUploadAsset(tenantId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      file,
      visibility,
      brandId,
      onProgress
    }: {
      file: File;
      visibility: string;
      brandId: string;
      onProgress?: (percentage: number) => void;
    }) => {
      if (!tenantId || !brandId) {
        throw new Error("missing_context");
      }
      const tusEndpoint = import.meta.env.VITE_TUS_ENDPOINT as string | undefined;
      if (tusEndpoint) {
        return new Promise((resolve, reject) => {
          const upload = new Upload(file, {
            endpoint: tusEndpoint,
            metadata: {
              filename: file.name,
              tenant_id: tenantId,
              brand_id: brandId,
              visibility
            },
            onProgress: (bytesUploaded, bytesTotal) => {
              if (onProgress) {
                onProgress(Math.round((bytesUploaded / bytesTotal) * 100));
              }
            },
            onSuccess: resolve,
            onError: reject
          });
          upload.start();
        });
      }
      const formData = new FormData();
      formData.append("tenant_id", tenantId);
      formData.append("brand_id", brandId);
      formData.append("visibility", visibility);
      formData.append("file", file);
      return apiClient.post("/admin/knowledge_assets/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress(progressEvent) {
          if (progressEvent.total && onProgress) {
            onProgress(Math.round((progressEvent.loaded / progressEvent.total) * 100));
          }
        }
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries();
    }
  });
}
