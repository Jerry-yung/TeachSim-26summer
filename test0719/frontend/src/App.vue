<template>
  <div class="app-shell">
    <template v-if="!isLoginRoute">
      <AppSidebar v-if="!isClassroomRoute" />
      <div class="app-right">
        <AppTopbar v-if="!isInterviewRoute && !isClassroomRoute" />
        <main class="app-main">
          <router-view />
        </main>
      </div>
    </template>
    <template v-else>
      <div class="login-shell">
        <router-view />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from '@/components/AppSidebar.vue'
import AppTopbar from '@/components/AppTopbar.vue'
import { useAuthStore } from '@/stores/authStore'
import { primeHistorySessionsCache } from '@/api/ai'

const route = useRoute()
const authStore = useAuthStore()
const isLoginRoute = computed(() => route.path === '/login')
const isInterviewRoute = computed(() => route.path.startsWith('/interview'))
const isClassroomRoute = computed(() => route.path.startsWith('/classroom'))

watch(
  () => authStore.isLoggedIn,
  (loggedIn) => {
    if (loggedIn) {
      primeHistorySessionsCache({ limit: 50, offset: 0 })
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--color-bg);
}

.app-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.app-main {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.login-shell {
  flex: 1;
  min-width: 0;
  min-height: 100vh;
  display: flex;
}
</style>
