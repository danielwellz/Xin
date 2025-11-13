import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "./AuthProvider";

export function AuthGate() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const [token, setToken] = useState("");
  const [persist, setPersist] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    try {
      login(token.trim(), persist);
      setError(null);
    } catch {
      setError("Unable to parse token");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 to-slate-700">
      <div className="card w-full max-w-xl bg-white/95 text-left">
        <h1 className="text-2xl font-semibold">{t("auth.heading")}</h1>
        <p className="mt-2 text-sm text-slate-500">{t("auth.sampleHint")}</p>
        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <label className="block text-sm font-medium text-slate-700">
            {t("auth.tokenLabel")}
            <textarea
              data-testid="auth-token-input"
              className="mt-2 min-h-[140px] w-full rounded-xl border border-border bg-slate-50 px-3 py-2 text-sm focus:border-brand focus:ring-2 focus:ring-brand/40"
              value={token}
              onChange={(event) => setToken(event.target.value)}
            />
          </label>
          <label className="inline-flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={persist}
              onChange={(event) => setPersist(event.target.checked)}
              className="rounded border-slate-300 text-brand focus:ring-brand"
            />
            {t("auth.persist")}
          </label>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <button
            type="submit"
            className="w-full rounded-xl bg-brand px-4 py-3 text-base font-semibold text-white shadow-lg shadow-brand/40 transition hover:bg-brand/90"
          >
            {t("auth.submit")}
          </button>
        </form>
      </div>
    </div>
  );
}
