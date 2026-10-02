// 应用入口：注册 Pinia / ElementPlus / Router / i18n
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus, { ElMessage } from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import i18n from './i18n'

const app = createApp(App)
app.use(createPinia())
app.use(ElementPlus)
app.use(router)
app.use(i18n)

// 全局兜底：组件渲染期异常与未捕获 Promise 不再直接白屏
app.config.errorHandler = (err) => {
  console.error('Global error:', err)
  ElMessage.error(i18n.global.t('common.error'))
}
window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled rejection:', event.reason)
})

app.mount('#app')
