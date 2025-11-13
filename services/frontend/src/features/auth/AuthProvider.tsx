import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { jwtDecode } from "jwt-decode";

import { registerHttpContext } from "@/api/httpClient";

const TOKEN_STORAGE_KEY = "xin-operator-token";

type TokenClaims = {
  sub: string;
  roles: string[];
  tenant_id?: string;
  exp: number;
};

type AuthContextValue = {
  token: string | null;
  claims: TokenClaims | null;
  scopes: string[];
  login: (token: string, persist: boolean) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_STORAGE_KEY));
  const [claims, setClaims] = useState<TokenClaims | null>(() => {
    const stored = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!stored) {
      return null;
    }
    try {
      return jwtDecode<TokenClaims>(stored);
    } catch {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      return null;
    }
  });

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setClaims(null);
  }, []);

  const login = useCallback(
    (nextToken: string, persist: boolean) => {
      try {
        const decoded = jwtDecode<TokenClaims>(nextToken);
        setToken(nextToken);
        setClaims(decoded);
        if (persist) {
          localStorage.setItem(TOKEN_STORAGE_KEY, nextToken);
        } else {
          localStorage.removeItem(TOKEN_STORAGE_KEY);
        }
      } catch (error) {
        console.error("Failed to decode token", error);
        throw new Error("invalid_token");
      }
    },
    []
  );

  useEffect(() => {
    registerHttpContext({
      getToken: () => token
    });
  }, [token]);

  useEffect(() => {
    const handler = () => logout();
    window.addEventListener("xin:auth:expired", handler);
    return () => window.removeEventListener("xin:auth:expired", handler);
  }, [logout]);

  const value = useMemo(
    () => ({
      token,
      claims,
      scopes: claims?.roles ?? [],
      login,
      logout
    }),
    [claims, login, logout, token]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
