import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import type { ReactNode } from "react";

import { AuthProvider } from "@/features/auth/AuthProvider";
import { LocaleProvider } from "@/features/i18n/LocaleProvider";
import { TenantProvider } from "@/features/tenants/TenantContext";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1
    }
  }
});

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <LocaleProvider>
        <TenantProvider>
          <QueryClientProvider client={queryClient}>
            {children}
            {import.meta.env.DEV ? <ReactQueryDevtools position="bottom-right" /> : null}
          </QueryClientProvider>
        </TenantProvider>
      </LocaleProvider>
    </AuthProvider>
  );
}
