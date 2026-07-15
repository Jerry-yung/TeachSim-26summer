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

      <div class="user-chip">
        <div class="user-avatar">刘</div>
        <div class="user-info">
          <span class="user-name">刘至晗</span>
          <span class="user-role">实习教师</span>
        </div>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="chevron">
          <polyline points="6 9 12 15 18 9" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const pageTitle = computed(() => {
  if (route.path.startsWith('/interview')) return '课堂配置 · 问卷填写'
  if (route.path.startsWith('/classroom')) return '虚拟课堂模拟'
  if (route.path.startsWith('/report')) return '课后分析报告'
  return '新建课堂'
})
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
</style>
