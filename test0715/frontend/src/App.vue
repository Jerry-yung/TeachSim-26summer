<template>
  <div class="app-shell">
    <AppSidebar />
    <div class="app-right">
      <AppTopbar v-if="!isInterviewRoute" />
      <main class="app-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from '@/components/AppSidebar.vue'
import AppTopbar from '@/components/AppTopbar.vue'

const route = useRoute()
const isInterviewRoute = computed(() => route.path.startsWith('/interview'))
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
</style>
