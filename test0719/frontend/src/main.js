import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router/index.js'
import { useAuthStore } from '@/stores/authStore.js'
import './style.css'

const pinia = createPinia()
const app = createApp(App)
app.use(pinia)
app.use(router)
void useAuthStore(pinia).initialize()
app.mount('#app')
