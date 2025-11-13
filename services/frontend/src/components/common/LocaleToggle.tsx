import { Menu, Transition } from "@headlessui/react";
import { Languages } from "lucide-react";
import { Fragment } from "react";
import { useTranslation } from "react-i18next";

import { useLocale } from "@/features/i18n/LocaleProvider";

const LOCALE_LABELS: Record<string, string> = {
  en: "English",
  fa: "فارسی"
};

export function LocaleToggle() {
  const { locale, setLocale } = useLocale();
  const { t } = useTranslation();

  return (
    <Menu as="div" className="relative inline-block text-left">
      <Menu.Button
        className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1 text-sm font-medium text-surface-foreground shadow-sm transition hover:bg-slate-100 rtl:flex-row-reverse"
        aria-label={t("i18n.localeToggle")}
      >
        <Languages className="h-4 w-4" />
        <span>{LOCALE_LABELS[locale]}</span>
      </Menu.Button>
      <Transition
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <Menu.Items className="absolute end-0 mt-2 w-48 origin-top-right rounded-lg bg-white shadow-card ring-1 ring-black/5 focus:outline-none">
          {Object.entries(LOCALE_LABELS).map(([key, label]) => (
            <Menu.Item key={key}>
              {({ active }) => (
                <button
                  type="button"
                  onClick={() => setLocale(key as "en" | "fa")}
                  className={`flex w-full items-center justify-between px-4 py-2 text-sm ${active ? "bg-slate-100" : ""}`}
                >
                  <span>{label}</span>
                  {locale === key ? "✓" : null}
                </button>
              )}
            </Menu.Item>
          ))}
        </Menu.Items>
      </Transition>
    </Menu>
  );
}
