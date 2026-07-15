import { createRouter, createWebHistory } from 'vue-router'
import SetupView from '@/views/SetupView.vue'
import InterviewView from '@/views/InterviewView.vue'
import ReportView from '@/views/ReportView.vue'
import ClassroomView from '@/views/ClassroomView.vue'

const routes = [
  { path: '/', redirect: '/setup' },
  { path: '/setup', component: SetupView },
  { path: '/interview/:sessionId', component: InterviewView },
  { path: '/classroom/:sessionId', component: ClassroomView },
  { path: '/report/:sessionId', component: ReportView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
