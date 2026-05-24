// src/plugins/i18n.ts
import { createI18n } from 'vue-i18n'
import zh from '@/locales/zh'
import en from '@/locales/en'

const savedLang = localStorage.getItem('lang') ?? 'zh'

const i18n = createI18n({
  legacy: false,        // Use Composition API mode
  locale: savedLang,
  fallbackLocale: 'zh',
  messages: { zh, en },
})

export default i18n
