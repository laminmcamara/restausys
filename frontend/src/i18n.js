import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import en from './locales/en/translation.json';
import es from './locales/es/translation.json';
import zh from './locales/zh/translation.json';       // Simplified Chinese
import zhHK from './locales/zh-HK/translation.json'; // Cantonese / Traditional Chinese (HK)
import fr from './locales/fr/translation.json';
import tr from './locales/tr/translation.json';
import ur from './locales/ur/translation.json';
import ar from './locales/ar/translation.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      es: { translation: es },
      zh: { translation: zh },
      'zh-HK': { translation: zhHK },
      fr: { translation: fr },
      tr: { translation: tr },
      ur: { translation: ur },
      ar: { translation: ar },
    },
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
    react: { useSuspense: false },
  });

export default i18n;