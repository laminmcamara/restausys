import { useTranslation } from "react-i18next";
import { ChevronDown } from "lucide-react";
import { useState } from "react";

const LANGUAGES = [
  { code: 'en', labelKey: 'languages.en' },
  { code: 'es', labelKey: 'languages.es' },
  { code: 'zh', labelKey: 'languages.zh' },
  { code: 'fr', labelKey: 'languages.fr' },
  { code: 'tr', labelKey: 'languages.tr' },
  { code: 'ur', labelKey: 'languages.ur' },
  { code: 'ar', labelKey: 'languages.ar' },
];
  // add more

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const [open, setOpen] = useState(false);

  const current =
    LANGUAGES.find((l) => l.code === i18n.language) || LANGUAGES[0];

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center space-x-2 text-sm font-medium text-slate-700 hover:text-amber-600 transition">
        <span>{current.label}</span>
        <ChevronDown size={16} />
      </button>

      {open && (
        <div className="absolute right-0 top-8 z-50 w-40 rounded-xl border border-slate-200 bg-white py-2 shadow-lg">
          {LANGUAGES.map((lng) => (
            <button
              key={lng.code}
              type="button"
              onClick={() => {
                i18n.changeLanguage(lng.code);
                setOpen(false);
              }}
              className={`block w-full text-left px-4 py-2 text-sm transition ${
                lng.code === i18n.language
                  ? "bg-amber-50 text-amber-700"
                  : "text-slate-700 hover:bg-slate-100"
              }`}>
              {lng.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
