import { enStrings } from "../locales/en";
import { faStrings } from "../locales/fa";
import type { Locale, LocaleStrings, WidgetOptions } from "../types";

const builtIns: Record<Locale, LocaleStrings> = {
  en: enStrings,
  fa: faStrings
};

export function resolveStrings(locale: Locale, options: WidgetOptions): { locale: Locale; strings: LocaleStrings } {
  const overrides = options.strings?.[locale];
  const fallback = options.strings?.[options.defaultLocale ?? "en"];
  const merged = {
    ...builtIns[locale],
    ...(fallback ?? {}),
    ...(overrides ?? {})
  };
  return { locale, strings: merged };
}

export function toggleLocale(current: Locale): Locale {
  return current === "en" ? "fa" : "en";
}
