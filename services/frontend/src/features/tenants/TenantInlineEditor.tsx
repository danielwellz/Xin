import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import type { Tenant } from "@/api/schemas";

import { useUpdateTenant } from "./api";

type FormValues = {
  name: string;
  timezone: string;
  metadataJson: string;
};

export function TenantInlineEditor({ tenant }: { tenant: Tenant }) {
  const { t } = useTranslation();
  const { register, handleSubmit, reset } = useForm<FormValues>({
    defaultValues: {
      name: tenant.name,
      timezone: tenant.timezone,
      metadataJson: JSON.stringify(tenant.metadata ?? {}, null, 2)
    }
  });
  const mutation = useUpdateTenant();
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");

  const onSubmit = handleSubmit(async (values) => {
    try {
      const metadata = values.metadataJson ? JSON.parse(values.metadataJson) : {};
      await mutation.mutateAsync({
        tenantId: tenant.id,
        payload: {
          name: values.name,
          timezone: values.timezone,
          metadata
        }
      });
      setStatus("success");
      reset(values);
    } catch (error) {
      console.error(error);
      setStatus("error");
    }
  });

  return (
    <form className="card space-y-4" onSubmit={onSubmit}>
      <div>
        <h3 className="text-lg font-semibold">{t("tenant.inlineEdit")}</h3>
        <p className="text-sm text-slate-500">{tenant.id}</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="text-sm font-medium text-slate-600">
          {t("tenant.listTitle")}
          <input
            className="mt-1 w-full rounded-xl border border-border px-3 py-2 text-sm focus:border-brand focus:ring-2 focus:ring-brand/30"
            {...register("name")}
          />
        </label>
        <label className="text-sm font-medium text-slate-600">
          {t("tenant.timezone")}
          <input
            className="mt-1 w-full rounded-xl border border-border px-3 py-2 text-sm focus:border-brand focus:ring-2 focus:ring-brand/30"
            {...register("timezone")}
          />
        </label>
      </div>
      <label className="text-sm font-medium text-slate-600">
        {t("tenant.metadata")}
        <textarea
          className="mt-1 h-36 w-full rounded-xl border border-border bg-slate-50 px-3 py-2 text-sm focus:border-brand focus:ring-2 focus:ring-brand/30"
          {...register("metadataJson")}
        />
      </label>
      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={() =>
            reset({
              name: tenant.name,
              timezone: tenant.timezone,
              metadataJson: JSON.stringify(tenant.metadata ?? {}, null, 2)
            })
          }
          className="rounded-xl border border-border px-4 py-2 text-sm font-semibold text-slate-600"
        >
          {t("actions.cancel")}
        </button>
        <button
          type="submit"
          className="rounded-xl bg-brand px-5 py-2 text-sm font-semibold text-white shadow-brand/30"
          disabled={mutation.isPending}
        >
          {mutation.isPending ? "…" : t("actions.save")}
        </button>
      </div>
      {status === "success" ? (
        <p className="text-sm text-emerald-600">Saved! Audit trail updated.</p>
      ) : null}
      {status === "error" ? <p className="text-sm text-red-600">Failed to save.</p> : null}
    </form>
  );
}
