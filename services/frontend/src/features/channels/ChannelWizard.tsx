import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { apiClient } from "@/api/httpClient";
import { ChannelSchema, ChannelTypeSchema } from "@/api/schemas";
import { ScopeGuard } from "@/features/auth/useScope";
import { useTenantContext } from "@/features/tenants/TenantContext";

type WizardForm = {
  channel_type: "instagram" | "telegram" | "whatsapp" | "web";
  brand_name: string;
  display_name: string;
  webhook_url: string;
  credentials: Record<string, string>;
};

const steps = ["channelWizard.selectType", "channelWizard.configCredentials", "channelWizard.review"];

export function ChannelWizard() {
  const { selectedTenantId } = useTenantContext();
  const { register, handleSubmit, watch } = useForm<WizardForm>({
    defaultValues: {
      channel_type: "web",
      brand_name: "",
      display_name: "",
      webhook_url: "",
      credentials: {}
    }
  });
  const [step, setStep] = useState(0);
  const { t } = useTranslation();
  const [secret, setSecret] = useState<string | null>(null);

  const onSubmit = handleSubmit(async (values) => {
    if (!selectedTenantId) {
      return;
    }
    const response = await apiClient.post("/admin/channels", {
      tenant_id: selectedTenantId,
      brand_name: values.brand_name,
      display_name: values.display_name,
      channel_type: values.channel_type,
      credentials: {
        webhook_url: values.webhook_url,
        ...values.credentials
      }
    });
    const parsed = ChannelSchema.safeParse(response.data);
    setSecret(parsed.success ? parsed.data.hmac_secret ?? null : null);
    setStep(2);
  });

  const currentStepKey = steps[step];
  const channelType = watch("channel_type");

  return (
    <ScopeGuard
      allow="platform_admin"
      fallback={<p className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">{t("rbac.restricted")}</p>}
    >
      <div className="card space-y-6">
        <div>
          <p className="text-sm uppercase tracking-wide text-slate-400">
            {t("channelWizard.step", { current: step + 1, total: steps.length })}
          </p>
          <h2 className="text-2xl font-semibold">{t(currentStepKey)}</h2>
        </div>
        <form className="space-y-4" onSubmit={onSubmit}>
          {step === 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {ChannelTypeSchema.options.map((value) => (
                <label
                  key={value}
                  className={`cursor-pointer rounded-xl border px-4 py-3 text-sm font-semibold capitalize ${
                    channelType === value ? "border-brand bg-brand/5" : "border-border"
                  }`}
                >
                  <input type="radio" value={value} {...register("channel_type")} className="hidden" />
                  {value}
                </label>
              ))}
            </div>
          ) : null}
          {step === 1 ? (
            <>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="text-sm font-medium text-slate-600">
                  {t("channelWizard.brandName")}
                  <input
                    {...register("brand_name", { required: true })}
                    className="mt-1 w-full rounded-xl border border-border px-3 py-2 text-sm"
                  />
                </label>
                <label className="text-sm font-medium text-slate-600">
                  {t("channelWizard.displayName")}
                  <input
                    {...register("display_name", { required: true })}
                    className="mt-1 w-full rounded-xl border border-border px-3 py-2 text-sm"
                  />
                </label>
              </div>
              <label className="text-sm font-medium text-slate-600">
                {t("channelWizard.webhookUrl")}
                <input
                  {...register("webhook_url", { required: true })}
                  placeholder="https://hooks.yourbrand.com/xin"
                  className="mt-1 w-full rounded-xl border border-border px-3 py-2 text-sm"
                />
              </label>
            </>
          ) : null}
          {step === 2 && secret ? (
            <div className="rounded-2xl border border-dashed border-brand/40 bg-brand/5 p-4 text-sm">
              <p className="font-semibold">{t("channelWizard.copySecret")}</p>
              <code className="mt-2 block break-all rounded-xl bg-white/80 p-3 text-xs">{secret}</code>
              <button
                type="button"
                onClick={() => navigator.clipboard.writeText(secret)}
                className="mt-3 rounded-xl bg-brand px-4 py-2 text-xs font-semibold text-white"
              >
                {t("actions.copy")}
              </button>
            </div>
          ) : null}
          <div className="flex justify-between">
            <button
              type="button"
              onClick={() => setStep((prev) => Math.max(prev - 1, 0))}
              className="rounded-xl border border-border px-4 py-2 text-sm"
              disabled={step === 0}
            >
              {t("actions.cancel")}
            </button>
            <button
              type={step === steps.length - 1 ? "submit" : "button"}
              onClick={step < steps.length - 1 ? () => setStep((prev) => prev + 1) : undefined}
              className="rounded-xl bg-brand px-5 py-2 text-sm font-semibold text-white"
            >
              {step === steps.length - 1 ? t("actions.save") : t("actions.preview")}
            </button>
          </div>
        </form>
      </div>
    </ScopeGuard>
  );
}
