"use client";

import { useLanguage } from "@/lib/i18n";

export function LanguageToggle() {
  const { locale, toggleLocale, t } = useLanguage();

  return (
    <button
      type="button"
      onClick={toggleLocale}
      aria-label={t.common.languageToggleAria}
      className="fixed right-4 top-4 z-30 inline-flex items-center gap-1 rounded-full border border-neutral-700 bg-neutral-950/85 px-2 py-1 text-xs font-medium text-neutral-300 shadow-lg shadow-black/30 backdrop-blur transition hover:border-neutral-500 hover:text-neutral-100"
    >
      <span
        className={
          locale === "en"
            ? "rounded-full bg-fuchsia-500 px-2 py-0.5 text-white"
            : "px-2 py-0.5"
        }
      >
        EN
      </span>
      <span
        className={
          locale === "zh"
            ? "rounded-full bg-fuchsia-500 px-2 py-0.5 text-white"
            : "px-2 py-0.5"
        }
      >
        中文
      </span>
    </button>
  );
}
