import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { supportedLocales } from "@/i18n/config";

type Locale = (typeof supportedLocales)[number];

type LocaleContextValue = {
  locale: Locale;
  toggle: () => void;
  setLocale: (locale: Locale) => void;
};

const LocaleContext = createContext<LocaleContextValue | undefined>(undefined);

const getDirection = (locale: Locale) => (locale === "fa" ? "rtl" : "ltr");

export function LocaleProvider({ children }: { children: ReactNode }) {
  const { i18n } = useTranslation();
  const initialLocale = supportedLocales.includes(i18n.language as Locale)
    ? (i18n.language as Locale)
    : "en";
  const [locale, setLocaleState] = useState<Locale>(initialLocale);

  const setLocale = useCallback(
    (next: Locale) => {
      setLocaleState(next);
      void i18n.changeLanguage(next);
    },
    [i18n]
  );

  const toggle = useCallback(() => {
    setLocale((locale === "en" ? "fa" : "en") as Locale);
  }, [locale, setLocale]);

  useEffect(() => {
    const dir = getDirection(locale);
    const html = document.documentElement;
    html.lang = locale;
    html.dir = dir;
    document.body.dataset.locale = locale;
  }, [locale]);

  const value = useMemo(
    () => ({
      locale,
      toggle,
      setLocale
    }),
    [locale, setLocale, toggle]
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const context = useContext(LocaleContext);
  if (!context) {
    throw new Error("useLocale must be used within LocaleProvider");
  }
  return context;
}
