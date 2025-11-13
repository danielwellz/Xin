import { Building2, CircuitBoard, Globe, Layers, Settings2, Zap } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";

import { LocaleToggle } from "@/components/common/LocaleToggle";
import { useAuth } from "@/features/auth/AuthProvider";

type NavItem = {
  path: string;
  labelKey: string;
  icon: typeof Building2;
  scopes?: string[];
};

const navItems: NavItem[] = [
  { path: "/tenants", labelKey: "nav.tenants", icon: Building2, scopes: ["platform_admin"] },
  { path: "/channels/wizard", labelKey: "nav.channels", icon: Settings2, scopes: ["platform_admin"] },
  { path: "/policies", labelKey: "nav.policies", icon: Layers, scopes: ["platform_admin", "tenant_operator"] },
  { path: "/knowledge", labelKey: "nav.knowledge", icon: Globe, scopes: ["platform_admin", "tenant_operator"] },
  { path: "/automation", labelKey: "nav.automation", icon: Zap, scopes: ["platform_admin"] },
  { path: "/observability", labelKey: "nav.observability", icon: CircuitBoard, scopes: ["platform_admin", "tenant_operator"] }
];

export function LayoutShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const { claims, logout, scopes } = useAuth();

  return (
    <div className="flex min-h-screen bg-slate-100">
      <nav className="hidden w-64 flex-shrink-0 flex-col border-e border-slate-200 bg-white/95 p-6 text-sm lg:flex">
        <div>
          <p className="text-lg font-display font-semibold text-slate-900">{t("app.title")}</p>
          <p className="text-xs text-slate-500">{t("app.tagline")}</p>
        </div>
        <ul className="mt-8 space-y-1 text-sm font-medium text-slate-600">
          {navItems.map((item) => {
            const allowed = !item.scopes || item.scopes.some((scope) => scopes.includes(scope));
            if (!allowed) {
              return null;
            }
            return (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-xl px-3 py-2 transition ${
                      isActive ? "bg-brand/10 text-brand" : "hover:bg-slate-100"
                    }`
                  }
                >
                  <item.icon className="h-4 w-4" />
                  {t(item.labelKey)}
                </NavLink>
              </li>
            );
          })}
        </ul>
        <div className="mt-auto space-y-2">
          <LocaleToggle />
          <div className="rounded-xl border border-slate-200 p-3 text-xs text-slate-500">
            <p className="font-semibold text-slate-700">{claims?.sub}</p>
            <p>{t("auth.scopes")}: {scopes.join(", ")}</p>
            {claims?.tenant_id ? <p>{t("auth.tenantScope")}: {claims.tenant_id}</p> : null}
          </div>
          <button
            type="button"
            onClick={logout}
            className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-600"
          >
            Sign out
          </button>
        </div>
      </nav>
      <main className="flex-1 overflow-y-auto p-6">
        <header className="mb-6 flex flex-col gap-4 rounded-3xl bg-gradient-to-br from-brand/10 via-white to-white p-6 shadow-card md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">{new Date().toLocaleString()}</p>
            <h1 className="text-2xl font-semibold text-slate-900">{t("app.title")}</h1>
          </div>
          <div className="flex items-center gap-3">
            <LocaleToggle />
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}
