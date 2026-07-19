<template>
  <header class="topbar">
    <div class="topbar-left">
      <span class="topbar-title">{{ pageTitle }}</span>
    </div>
    <div class="topbar-right">
      <button class="icon-btn" title="通知">
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        <span class="notif-dot"></span>
      </button>

      <div ref="chipRef" class="user-chip" @click="showMenu = !showMenu">
        <div class="user-avatar">{{ auth.avatarChar }}</div>
        <div class="user-info">
          <span class="user-name">{{ auth.user?.name }}</span>
          <span class="user-role">{{ auth.user?.role }}</span>
        </div>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="chevron">
          <polyline points="6 9 12 15 18 9" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>

      <div v-if="showMenu" class="user-menu" @click.stop>
        <div class="menu-header">
          <div class="menu-avatar">{{ auth.avatarChar }}</div>
          <div>
            <div class="menu-name">{{ auth.user?.name }}</div>
            <div class="menu-role">{{ auth.user?.role }}</div>
          </div>
        </div>
        <div class="menu-divider"></div>
        <button class="menu-item logout" @click="doLogout">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
          退出登录
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore.js'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const showMenu = ref(false)
const chipRef = ref(null)

const pageTitle = computed(() => {
  if (route.path.startsWith('/setup')) return '新建课堂'
  if (route.path.startsWith('/interview')) return '课堂配置 · 问卷填写'
  if (route.path.startsWith('/classroom')) return '虚拟课堂模拟'
  if (route.path.startsWith('/report')) return '课后分析报告'
  if (route.path.startsWith('/history')) return '历史课堂'
  if (route.path.startsWith('/ability-profile')) return '能力画像'
  return '新建课堂'
})

async function doLogout() {
  await auth.logout()
  showMenu.value = false
  router.push('/login')
}

function onClickOutside(e) {
  if (chipRef.value && !chipRef.value.contains(e.target)) {
    showMenu.value = false
  }
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.topbar {
  height: 52px;
  min-height: 52px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-card);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 20;
}

.topbar-title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-btn {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all 0.15s;
  position: relative;
}

.icon-btn:hover {
  background: var(--color-bg);
  color: var(--color-text-secondary);
}

.notif-dot {
  position: absolute;
  top: 7px;
  right: 7px;
  width: 7px;
  height: 7px;
  background: #EF4444;
  border-radius: 50%;
  border: 1.5px solid white;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 5px 10px 5px 5px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.user-chip:hover {
  background: var(--color-bg);
  border-color: var(--color-border);
}

.user-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2563EB, #7C3AED);
  color: white;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  line-height: 1;
}

.user-role {
  font-size: 10.5px;
  color: var(--color-text-muted);
  line-height: 1;
}

.chevron {
  color: var(--color-text-muted);
}

/* Dropdown */
.topbar-right {
  position: relative;
}

.user-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 200px;
  background: white;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 30px rgba(0,0,0,0.12);
  z-index: 100;
  overflow: hidden;
  animation: fadeInDown 0.15s ease;
}

@keyframes fadeInDown {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

.menu-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
}

.menu-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2563EB, #7C3AED);
  color: white;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.menu-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-text);
  line-height: 1.2;
}

.menu-role {
  font-size: 11.5px;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.menu-divider {
  height: 1px;
  background: var(--color-border-light);
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 11px 16px;
  font-size: 13.5px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background 0.12s;
  text-align: left;
}

.menu-item:hover { background: var(--color-bg); }

.menu-item.logout {
  color: #DC2626;
}

.menu-item.logout:hover {
  background: #FEF2F2;
}
</style>
