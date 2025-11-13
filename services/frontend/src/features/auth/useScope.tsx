import { PropsWithChildren } from "react";

import { useAuth } from "./AuthProvider";

export function useHasScope(required: string | string[]) {
  const { scopes } = useAuth();
  const list = Array.isArray(required) ? required : [required];
  return list.some((scope) => scopes.includes(scope));
}

type ScopeGuardProps = PropsWithChildren<{
  allow: string | string[];
  fallback?: JSX.Element | null;
}>;

export function ScopeGuard({ allow, fallback = null, children }: ScopeGuardProps) {
  const allowed = useHasScope(allow);
  if (!allowed) {
    return fallback;
  }
  return <>{children}</>;
}
