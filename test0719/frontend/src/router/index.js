import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/authStore.js'
import SetupView from '@/views/SetupView.vue'
import InterviewView from '@/views/InterviewView.vue'
import ReportView from '@/views/ReportView.vue'
import ClassroomView from '@/views/ClassroomView.vue'
import LoginView from '@/views/LoginView.vue'
import HistoryView from '@/views/HistoryView.vue'
import AbilityProfileView from '@/views/AbilityProfileView.vue'

const routes = [
  { path: '/login', component: LoginView, meta: { public: true } },
  { path: '/', redirect: '/setup' },
  { path: '/setup', component: SetupView },
  { path: '/interview/:sessionId', component: InterviewView },
  { path: '/classroom/:sessionId', component: ClassroomView },
  { path: '/report/:sessionId', component: ReportView },
  { path: '/history', component: HistoryView },
  { path: '/ability-profile', component: AbilityProfileView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const AUTH_INIT_TIMEOUT_MS = 12_000

function initializeAuthWithTimeout(auth) {
  return Promise.race([
    auth.initialize(),
    new Promise((resolve) => {
      setTimeout(resolve, AUTH_INIT_TIMEOUT_MS)
    }),
  ])
}

router.beforeEach((to) => {
  const auth = useAuthStore()
  return initializeAuthWithTimeout(auth).then(() => {
    if (!to.meta.public && !auth.isLoggedIn) {
      return '/login'
    }
    if (to.path === '/login' && auth.isLoggedIn) {
      return '/setup'
    }
    return true
  })
})

export default router
