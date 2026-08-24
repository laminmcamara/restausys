import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown } from "lucide-react";

const LANGUAGES = [
  { code: "en", labelKey: "languages.en" },
  { code: "es", labelKey: "languages.es" },
  { code: "zh", labelKey: "languages.zh" },
  { code: "fr", labelKey: "languages.fr" },
  { code: "tr", labelKey: "languages.tr" },
  { code: "ur", labelKey: "languages.ur" },
  { code: "ar", labelKey: "languages.ar" },
];

export default function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);

  const activeCode = i18n.resolvedLanguage || i18n.language || "en";

  const current =
    LANGUAGES.find((language) => language.code === activeCode) || LANGUAGES[0];

  return (
    <div className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-2 whitespace-nowrap text-sm font-medium text-slate-700 transition hover:text-amber-600"
        aria-haspopup="listbox"
        aria-expanded={open}>
        <span>{t(current.labelKey)}</span>
        <ChevronDown
          size={16}
          className={`transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div
          className="absolute right-0 top-8 z-50 w-40 rounded-xl border border-slate-200 bg-white py-2 shadow-lg"
          role="listbox">
          {LANGUAGES.map((language) => (
            <button
              key={language.code}
              type="button"
              onClick={() => {
                i18n.changeLanguage(language.code);
                setOpen(false);
              }}
              className={`block w-full px-4 py-2 text-left text-sm transition ${
                language.code === activeCode
                  ? "bg-amber-50 text-amber-700"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
              role="option"
              aria-selected={language.code === activeCode}>
              {t(language.labelKey)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
