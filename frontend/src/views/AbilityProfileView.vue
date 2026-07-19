<template>
  <div class="profile-view">
    <div class="header">
      <h2>能力画像</h2>
      <span class="meta">已完成课堂数：{{ sessionCount }}节</span>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <div v-if="loading" class="loading">能力画像加载中…</div>
    <div v-else-if="!sections.length" class="empty">暂无可用于画像的课堂报告数据</div>

    <div v-else class="section-list">
      <section v-for="section in sections" :key="section.key" class="profile-card">
        <div class="card-title">{{ section.title }}</div>
        <div class="metric-list">
          <div v-for="metric in section.metrics" :key="metric.key" class="metric-row">
            <div class="metric-label">{{ metric.label }}</div>
            <div class="metric-value-wrap">
              <span class="metric-value">{{ formatMetric(metric.value) }}</span>
              <span class="metric-unit">{{ metric.unit }}</span>
              <span
                v-if="metric.trend === 'up'"
                class="trend"
                :class="metric.trend_tone === 'good' ? 'good' : 'bad'"
                title="最近三节相对整体变化"
              >↑</span>
              <span
                v-else-if="metric.trend === 'down'"
                class="trend"
                :class="metric.trend_tone === 'good' ? 'good' : 'bad'"
                title="最近三节相对整体变化"
              >↓</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { fetchAbilityProfile } from '@/api/ai'

const loading = ref(false)
const error = ref('')
const sections = ref([])
const sessionCount = ref(0)

function formatMetric(value) {
  const num = Number(value || 0)
  return Number.isFinite(num) ? num.toFixed(2) : '0.00'
}

async function loadProfile() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchAbilityProfile()
    sections.value = Array.isArray(data?.sections) ? data.sections : []
    sessionCount.value = Number(data?.session_count || 0)
  } catch (err) {
    error.value = err?.message || '能力画像加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadProfile()
})
</script>

<style scoped>
.profile-view { padding: 20px 28px; color: #0f172a; }
.header { display: flex; align-items: baseline; gap: 10px; margin-bottom: 14px; }
.header h2 { margin: 0; font-size: 24px; font-weight: 800; color: #020617; }
.meta { font-size: 12px; color: #64748b; }
.loading, .empty { margin-top: 20px; color: #64748b; }
.error { color: #dc2626; margin: 10px 0; }

.section-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 14px;
}
.profile-card {
  border: 1px solid #dbe3ee;
  border-radius: 14px;
  background: #f8fafc;
  padding: 14px;
}
.card-title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 10px;
}
.metric-list { display: flex; flex-direction: column; gap: 8px; }
.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #e2e8f0;
}
.metric-label { font-size: 13px; color: #334155; }
.metric-value-wrap { display: flex; align-items: center; gap: 5px; }
.metric-value {
  font-variant-numeric: tabular-nums;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}
.metric-unit { font-size: 11px; color: #64748b; }
.trend { font-size: 14px; font-weight: 800; margin-left: 2px; }
.trend.good { color: #16a34a; }
.trend.bad { color: #dc2626; }
</style>
