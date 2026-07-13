import { createI18n } from 'vue-i18n'
import zh from './zh'
import en from './en'

const savedLang = typeof window !== 'undefined'
  ? localStorage.getItem('language') || 'zh'
  : 'zh'

const i18n = createI18n({
  legacy: false,
  locale: savedLang,
  fallbackLocale: 'zh',
  messages: {
    zh,
    en
  }
})

// 启动时从后端同步语言配置
if (typeof window !== 'undefined') {
  fetch('/api/v1/i18n/config')
    .then(res => res.json())
    .then(config => {
      if (config.supported_languages) {
        localStorage.setItem('supported_languages', JSON.stringify(config.supported_languages))
      }
      // 如果 localStorage 没有语言设置，使用后端默认语言
      if (!localStorage.getItem('language') && config.default_language) {
        localStorage.setItem('language', config.default_language)
        i18n.global.locale.value = config.default_language
      }
    })
    .catch(() => {
      // 后端不可用时，使用前端默认配置
    })
}

export default i18n
