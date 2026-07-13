import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import router from './router'
import App from './App.vue'
import i18n from './locale'

const app = createApp(App)

app.use(createPinia())
app.use(ElementPlus)
app.use(router)
app.use(i18n)

app.mount('#app')