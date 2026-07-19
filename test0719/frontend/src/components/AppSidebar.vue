<template>
  <aside class="sidebar">
    <div class="sidebar-logo">
      <div class="logo-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M12 3L2 8l10 5 10-5-10-5z" fill="currentColor" opacity="0.9"/>
          <path d="M2 16l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <path d="M2 12l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </div>
      <span class="logo-text">TeachSim</span>
    </div>

    <nav class="sidebar-nav">
      <div class="nav-section">
        <span class="nav-label">课程训练</span>
        <router-link to="/setup" class="nav-item" :class="{ active: isSetupRoute }">
          <span class="nav-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
          </span>
          新建课堂
        </router-link>
        <router-link to="/history" class="nav-item" :class="{ active: route.path === '/history' || isHistoryReportRoute }">
          <span class="nav-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
          </span>
          历史课堂
        </router-link>
      </div>

      <div class="nav-section">
        <span class="nav-label">我的成长</span>
        <router-link to="/ability-profile" class="nav-item" :class="{ active: route.path === '/ability-profile' }">
          <span class="nav-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
          </span>
          能力画像
        </router-link>
        <router-link :to="'/report/mock-session-001'" class="nav-item" :class="{ active: route.path === '/report/mock-session-001' }">
          <span class="nav-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
          </span>
          查看示例报告
        </router-link>
      </div>
    </nav>

    <div class="sidebar-footer">
      <div class="user-avatar">{{ auth.avatarChar }}</div>
      <div class="user-info">
        <span class="user-name">{{ auth.user?.name }}</span>
        <span class="user-role">{{ auth.user?.role }}</span>
      </div>
      <button class="logout-btn" title="退出登录" @click="doLogout">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
          <polyline points="16 17 21 12 16 7"/>
          <line x1="21" y1="12" x2="9" y2="12"/>
        </svg>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore.js'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const isSetupRoute = computed(() => (
  route.path.startsWith('/setup')
  || route.path.startsWith('/interview')
  || route.path.startsWith('/classroom')
))

const isHistoryReportRoute = computed(() => {
  if (!route.path.startsWith('/report/')) return false
  return route.path !== '/report/mock-session-001'
})

async function doLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.sidebar {
  width: 228px;
  min-width: 228px;
  height: 100vh;
  background: var(--color-sidebar);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 18px 16px;
  border-bottom: 1px solid var(--color-border-light);
}

.logo-icon {
  width: 32px;
  height: 32px;
  background: var(--color-accent);
  color: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.logo-text {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.3px;
}

.sidebar-nav {
  flex: 1;
  padding: 12px 10px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.nav-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.7px;
  padding: 4px 8px 6px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  text-decoration: none;
  position: relative;
}

.nav-item:hover:not(.disabled) {
  background: var(--color-bg);
  color: var(--color-text);
}

.nav-item.active {
  background: #F0F4FF;
  color: var(--color-blue);
  font-weight: 600;
}

.nav-item.active .nav-icon {
  color: var(--color-blue);
}

.nav-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.nav-icon {
  display: flex;
  align-items: center;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.nav-badge {
  margin-left: auto;
  font-size: 10px;
  background: var(--color-bg);
  color: var(--color-text-muted);
  padding: 2px 6px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
}

.sidebar-footer {
  padding: 14px 16px;
  border-top: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #2563EB, #7C3AED);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}

.user-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: hidden;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
}

.user-role {
  font-size: 11px;
  color: var(--color-text-muted);
}

.logout-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.logout-btn:hover {
  background: #FEE2E2;
  color: #DC2626;
}
</style>
