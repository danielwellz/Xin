import { Clipboard, Plug, Webhook } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useChannels } from "@/features/tenants/api";
import { useTenantContext } from "@/features/tenants/TenantContext";

export function ChannelOverview() {
  const { selectedTenantId } = useTenantContext();
  const { t } = useTranslation();
  const { data: channels = [] } = useChannels(selectedTenantId);

  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{t("tenant.channels")}</h3>
        <a
          href="/channels/wizard"
          className="inline-flex items-center gap-2 rounded-xl border border-brand px-4 py-2 text-sm font-semibold text-brand"
        >
          <Plug className="h-4 w-4" />
          {t("actions.add")}
        </a>
      </div>
      <ul className="space-y-3">
        {channels.map((channel) => (
          <li
            key={channel.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border px-4 py-3"
          >
            <div>
              <p className="font-semibold capitalize">{channel.display_name}</p>
              <p className="text-xs uppercase text-slate-400">{channel.channel_type}</p>
            </div>
            {channel.hmac_secret ? (
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-lg border px-3 py-1 text-xs font-semibold text-slate-600"
                onClick={() => navigator.clipboard.writeText(channel.hmac_secret ?? "")}
              >
                <Clipboard className="h-3 w-3" />
                {t("actions.copy")}
              </button>
            ) : null}
          </li>
        ))}
        {channels.length === 0 ? (
          <li className="text-sm text-slate-500">No channels connected yet.</li>
        ) : null}
      </ul>
      <div className="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">
        <div className="flex items-center gap-2 font-semibold text-slate-700">
          <Webhook className="h-4 w-4" />
          {t("tenant.webhookDocs")}
        </div>
        <ol className="mt-2 list-decimal space-y-1 ps-6">
          <li>POST secrets to Vault as described in docs/RUNBOOK.md §5.</li>
          <li>Allowlisted callback host: `https://gateway.xinbot.ir/webhooks/&lt;channel&gt;`.</li>
          <li>Confirm handshake via Runbook §7 replay script.</li>
        </ol>
      </div>
    </div>
  );
}
