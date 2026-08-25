import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown } from "lucide-react";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
  { code: "zh", label: "中文 (简体)" }, // Simplified Chinese
  { code: "zh-HK", label: "粵語 (繁體)" }, // Cantonese (Traditional Chinese, HK)
  { code: "fr", label: "Français" },
  { code: "tr", label: "Türkçe" },
  { code: "ur", label: "اردو" },
  { code: "ar", label: "العربية" },
];

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const [open, setOpen] = useState(false);

  const activeCode = i18n.resolvedLanguage || i18n.language || "en";

  const current =
    LANGUAGES.find((language) => language.code === activeCode) || LANGUAGES[0];

  const handleChangeLanguage = (code) => {
    i18n.changeLanguage(code);
    setOpen(false);
  };

  return (
    <div className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-2 whitespace-nowrap text-sm font-medium text-slate-700 transition hover:text-amber-600"
        aria-haspopup="listbox"
        aria-expanded={open}>
        <span>{current.label}</span>
        <ChevronDown
          size={16}
          className={`transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div
          className="absolute right-0 top-8 z-50 w-48 rounded-xl border border-slate-200 bg-white py-2 shadow-lg"
          role="listbox">
          {LANGUAGES.map((language) => {
            const isActive = language.code === activeCode;

            return (
              <button
                key={language.code}
                type="button"
                onClick={() => handleChangeLanguage(language.code)}
                className={`block w-full px-4 py-2 text-left text-sm transition ${
                  isActive
                    ? "bg-amber-50 text-amber-700"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
                role="option"
                aria-selected={isActive}>
                {language.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
