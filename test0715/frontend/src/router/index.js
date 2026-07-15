import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/authStore.js'
import SetupView from '@/views/SetupView.vue'
import InterviewView from '@/views/InterviewView.vue'
import ReportView from '@/views/ReportView.vue'
import ClassroomView from '@/views/ClassroomView.vue'
import LoginView from '@/views/LoginView.vue'

const routes = [
  { path: '/login', component: LoginView, meta: { public: true } },
  { path: '/', redirect: '/setup' },
  { path: '/setup', component: SetupView },
  { path: '/interview/:sessionId', component: InterviewView },
  { path: '/classroom/:sessionId', component: ClassroomView },
  { path: '/report/:sessionId', component: ReportView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) {
    return '/login'
  }
  if (to.path === '/login' && auth.isLoggedIn) {
    return '/setup'
  }
})

export default router
