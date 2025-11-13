import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { registerHttpContext } from "@/api/httpClient";
import { useAuth } from "@/features/auth/AuthProvider";

type TenantContextValue = {
  selectedTenantId: string | null;
  setSelectedTenantId: (tenantId: string | null) => void;
};

const TenantContext = createContext<TenantContextValue | undefined>(undefined);
const STORAGE_KEY = "xin-active-tenant";

export function TenantProvider({ children }: { children: ReactNode }) {
  const { claims } = useAuth();
  const [selectedTenantId, setSelectedTenantIdState] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEY) ?? claims?.tenant_id ?? null;
  });

  const setSelectedTenantId = useCallback((tenantId: string | null) => {
    setSelectedTenantIdState(tenantId);
    if (tenantId) {
      localStorage.setItem(STORAGE_KEY, tenantId);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  useEffect(() => {
    registerHttpContext({
      getTenantId: () => selectedTenantId ?? claims?.tenant_id ?? null
    });
  }, [claims?.tenant_id, selectedTenantId]);

  const value = useMemo(
    () => ({
      selectedTenantId,
      setSelectedTenantId
    }),
    [selectedTenantId, setSelectedTenantId]
  );

  return <TenantContext.Provider value={value}>{children}</TenantContext.Provider>;
}

export function useTenantContext() {
  const context = useContext(TenantContext);
  if (!context) {
    throw new Error("useTenantContext must be used within TenantProvider");
  }
  return context;
}
