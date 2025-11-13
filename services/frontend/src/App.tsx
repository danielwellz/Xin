import { BrowserRouter } from "react-router-dom";

import { AppProviders } from "@/app/providers/AppProviders";
import { AppRouter } from "@/app/routes/AppRouter";
import { LayoutShell } from "@/components/layout/LayoutShell";
import { AuthGate } from "@/features/auth/AuthGate";
import { useAuth } from "@/features/auth/AuthProvider";

function ConsoleRoot() {
  const { token } = useAuth();
  if (!token) {
    return <AuthGate />;
  }
  return (
    <LayoutShell>
      <AppRouter />
    </LayoutShell>
  );
}

export default function App() {
  return (
    <AppProviders>
      <BrowserRouter>
        <ConsoleRoot />
      </BrowserRouter>
    </AppProviders>
  );
}
