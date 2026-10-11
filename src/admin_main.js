// 独立管理后台入口（不经主站 SPA / gh-pages，由 FastAPI 在 /admin 提供）
// 构建：vite build -c vite.admin.config.js → backend/app/static/admin
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus, { ElMessage } from 'element-plus'
import 'element-plus/dist/index.css'
import i18n from './i18n'
import './styles/admin-base.css'
import AdminGate from './components/AdminGate.vue'

const app = createApp(AdminGate)
app.use(createPinia())
app.use(ElementPlus)
app.use(i18n)

app.config.errorHandler = (err) => {
  console.error('Admin error:', err)
  ElMessage.error(i18n.global.t('common.error'))
}

app.mount('#admin-app')
