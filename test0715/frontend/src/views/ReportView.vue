<template>
  <div class="report-view">
    <!-- Top bar：移除分数，改为定性总体评价 -->
    <div class="report-topbar">
      <button class="back-btn" @click="router.push('/setup')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        返回
      </button>
      <div class="topbar-info">
        <span class="topbar-topic">{{ report.lesson_topic }}</span>
        <span class="topbar-meta">{{ report.subject }} · {{ report.class_info }} · {{ report.created_at }}</span>
      </div>
      <div class="topbar-level">
        <span class="level-badge">{{ report.overall_level }}</span>
        <span class="level-desc">{{ report.overall_desc }}</span>
      </div>
    </div>

    <div class="report-body">
      <!-- Row 1: 维度画像 + 硬指标 -->
      <div class="report-row two-col">
        <!-- 雷达图：展示维度形状，不展示分数数字 -->
        <div class="report-card radar-card">
          <div class="card-header">
            <span class="card-title">教学维度画像</span>
            <span class="card-badge">本节课</span>
          </div>
          <div ref="radarContainer" class="chart-container"></div>
          <!-- 维度定性标签 -->
          <div class="dim-tags">
            <div v-for="dim in report.dimensions" :key="dim.key" class="dim-tag">
              <span class="dim-label">{{ dim.label }}</span>
              <span class="dim-level" :class="dim.level.cls">{{ dim.level.label }}</span>
            </div>
          </div>
        </div>

        <!-- 教学硬指标 -->
        <div class="report-card stats-card">
          <div class="card-header">
            <span class="card-title">教学硬指标</span>
            <span class="card-hint">自动统计，无需 AI</span>
          </div>
          <div class="stats-grid">
            <div class="stat-item">
              <span class="stat-val">{{ report.hard_stats.total_duration_min }}<span class="stat-unit">min</span></span>
              <span class="stat-label">课堂时长</span>
            </div>
            <div class="stat-item">
              <span class="stat-val">{{ report.hard_stats.total_words.toLocaleString() }}<span class="stat-unit">字</span></span>
              <span class="stat-label">总字数</span>
            </div>
            <div class="stat-item" :class="{ warning: report.hard_stats.avg_speed_wpm > 150 }">
              <span class="stat-val">{{ report.hard_stats.avg_speed_wpm }}<span class="stat-unit">字/分</span></span>
              <span class="stat-label">平均语速</span>
              <span v-if="report.hard_stats.avg_speed_wpm > 150" class="stat-warn-tag">偏快</span>
            </div>
            <div class="stat-item" :class="{ warning: report.hard_stats.avg_wait_time_sec < 3 }">
              <span class="stat-val">{{ report.hard_stats.avg_wait_time_sec }}<span class="stat-unit">秒</span></span>
              <span class="stat-label">平均等待时间</span>
              <span v-if="report.hard_stats.avg_wait_time_sec < 3" class="stat-warn-tag">偏短</span>
            </div>
          </div>

          <!-- 口头禅统计 -->
          <div class="filler-section">
            <span class="filler-title">口头禅统计</span>
            <div class="filler-list">
              <div v-for="fw in report.hard_stats.filler_words" :key="fw.word" class="filler-item">
                <span class="filler-word">「{{ fw.word }}」</span>
                <div class="filler-bar-wrap">
                  <div
                    class="filler-bar"
                    :style="{ width: `${Math.min(fw.count / maxFillerCount * 100, 100)}%` }"
                    :class="{ hot: fw.count >= 10 }"
                  ></div>
                </div>
                <span class="filler-count" :class="{ hot: fw.count >= 10 }">{{ fw.count }}次</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 练习目标反馈：去掉分数，改为定性等级标签 -->
      <div v-if="report.custom_goal_feedback" class="report-card goal-card">
        <div class="goal-header">
          <span class="goal-icon">🎯</span>
          <div>
            <span class="goal-title">您的练习目标：{{ report.custom_goal_feedback.goal }}</span>
            <span class="goal-subtitle">本节课报告已针对此目标进行重点分析</span>
          </div>
          <div class="goal-level-wrap">
            <span class="goal-level-badge" :class="report.custom_goal_feedback.level.cls">
              {{ report.custom_goal_feedback.level.label }}
            </span>
          </div>
        </div>
        <p class="goal-feedback">{{ report.custom_goal_feedback.feedback }}</p>
      </div>

      <!-- Row 2: 时间分配 + 问答类型 -->
      <div class="report-row two-col">
        <div class="report-card">
          <div class="card-header">
            <span class="card-title">时间分配</span>
            <span class="card-hint">共 {{ report.duration_min }} 分钟</span>
          </div>
          <div class="time-bars">
            <div v-for="seg in report.time_distribution" :key="seg.segment" class="time-row">
              <span class="time-label">{{ seg.segment }}</span>
              <div class="time-bar-wrap">
                <div
                  class="time-bar-fill"
                  :style="{ width: `${(seg.duration / report.duration_min) * 100}%`, background: seg.color }"
                ></div>
              </div>
              <span class="time-duration">{{ seg.duration }}min</span>
            </div>
          </div>
        </div>

        <div class="report-card">
          <div class="card-header">
            <span class="card-title">问答类型分布</span>
            <span class="card-hint">{{ totalQuestions }} 次互动</span>
          </div>
          <div class="qa-list">
            <div v-for="qt in report.question_types" :key="qt.type" class="qa-row">
              <span class="qa-type">{{ qt.type }}</span>
              <div class="qa-bar-wrap">
                <div
                  class="qa-bar-fill"
                  :style="{ width: `${(qt.count / totalQuestions) * 100}%`, background: qt.color }"
                ></div>
              </div>
              <span class="qa-count">{{ qt.count }}次 <span class="qa-pct">({{ Math.round(qt.count / totalQuestions * 100) }}%)</span></span>
            </div>
          </div>

          <div class="qa-tip">
            <span class="qa-tip-icon">💡</span>
            <span>开放式提问仅占 {{ Math.round(report.question_types.find(q => q.type === '开放式')?.count / totalQuestions * 100) }}%，建议增加启发性问题</span>
          </div>
        </div>
      </div>

      <!-- AI 综合改进建议 -->
      <div class="report-card suggestions-card">
        <div class="card-header">
          <span class="card-title">AI 综合改进建议</span>
          <span class="card-badge blue">GPT-4o 生成</span>
        </div>
        <div class="suggestions-body" v-html="formattedSuggestions"></div>
      </div>

      <!-- 历史对比 -->
      <div v-if="report.is_improved" class="report-card history-card">
        <div class="history-header">
          <span class="history-icon">📈</span>
          <span class="history-title">历史对比</span>
          <span class="history-badge">有进步</span>
        </div>
        <p class="history-text" v-html="formattedHistory"></p>
      </div>

      <!-- 课堂关键节点 -->
      <div class="report-card">
        <div class="card-header">
          <span class="card-title">课堂关键节点</span>
        </div>
        <div class="events-list">
          <div v-for="ev in report.highlight_events" :key="ev.time" class="event-item" :class="ev.type">
            <div class="event-dot"></div>
            <span class="event-time">{{ ev.time }}</span>
            <span class="event-text">{{ ev.text }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { mockReport } from '@/mock/reportData.js'
import { fetchReport } from '@/api/ai.js'

const router = useRouter()
const route = useRoute()
const radarContainer = ref(null)
const report = reactive(JSON.parse(JSON.stringify(mockReport)))
let radarChart = null

const maxFillerCount = computed(() => Math.max(...report.hard_stats.filler_words.map((f) => f.count), 1))
const totalQuestions = computed(() => Math.max(report.question_types.reduce((s, q) => s + q.count, 0), 1))

const formattedSuggestions = computed(() =>
  (report.improvement_suggestions || '')
    .replace(/\n\n/g, '<br><br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/①|②|③/g, (m) => `<span class="list-marker">${m}</span>`),
)

const formattedHistory = computed(() =>
  (report.history_comparison || '').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'),
)

function levelLabel(val) {
  if (val >= 85) return '优秀'
  if (val >= 70) return '良好'
  if (val >= 60) return '待提升'
  return '需关注'
}

function updateChart() {
  if (!radarChart) return
  radarChart.setOption({
    backgroundColor: 'transparent',
    radar: {
      indicator: report.dimensions.map((d) => ({
        name: d.label,
        max: 100,
        min: 0,
      })),
      center: ['50%', '52%'],
      radius: '68%',
      splitNumber: 4,
      axisName: {
        color: '#6B7280',
        fontSize: 12,
        fontWeight: 500,
      },
      splitLine: {
        lineStyle: { color: '#F0F2F5', width: 1 },
      },
      splitArea: {
        areaStyle: { color: ['#F9FAFB', '#FFFFFF'] },
      },
      axisLine: {
        lineStyle: { color: '#E8ECF0' },
      },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: report.dimensions.map((d) => d._val),
            name: '本节课',
            symbol: 'circle',
            symbolSize: 5,
            areaStyle: {
              color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
                { offset: 0, color: 'rgba(37,99,235,0.3)' },
                { offset: 1, color: 'rgba(37,99,235,0.05)' },
              ]),
            },
            lineStyle: { color: '#2563EB', width: 2 },
            itemStyle: { color: '#2563EB' },
          },
        ],
      },
    ],
    tooltip: {
      trigger: 'item',
      formatter: () => {
        return report.dimensions
          .map((d) => `${d.label}：<strong>${levelLabel(d._val)}</strong>`)
          .join('<br>')
      },
    },
  })
}

async function loadReport() {
  const sessionId = String(route.params.sessionId || '')
  if (!sessionId || sessionId === 'mock-session-001') {
    updateChart()
    return
  }
  try {
    const data = await fetchReport(sessionId)
    Object.assign(report, data)
  } catch (err) {
    console.warn('[Report] 获取真实报告失败，回退到 mock：', err.message)
  } finally {
    updateChart()
  }
}

watch(
  () => report.dimensions.map((item) => item._val).join(','),
  () => updateChart(),
)

onMounted(async () => {
  if (!radarContainer.value) return

  radarChart = echarts.init(radarContainer.value)
  updateChart()
  await loadReport()

  const handleResize = () => radarChart?.resize()
  window.addEventListener('resize', handleResize)

  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    radarChart?.dispose()
    radarChart = null
  })
})
</script>

<style scoped>
.report-view {
  min-height: 100vh;
  background: var(--color-bg);
  display: flex;
  flex-direction: column;
}

.report-topbar {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 32px;
  background: var(--color-card);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 10;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border-radius: var(--radius-md);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.back-btn:hover {
  background: var(--color-border);
  color: var(--color-text);
}

.topbar-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.topbar-topic {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.3px;
}

.topbar-meta {
  font-size: 12px;
  color: var(--color-text-muted);
}

/* 定性总体评价标签 */
.topbar-level {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
}

.level-badge {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-blue);
  background: var(--color-blue-light);
  border: 1px solid #BFDBFE;
  padding: 4px 12px;
  border-radius: var(--radius-full);
}

.level-desc {
  font-size: 11.5px;
  color: var(--color-text-muted);
}

.report-body {
  padding: 28px 32px 60px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.report-row {
  display: flex;
  gap: 16px;
}

.two-col > * {
  flex: 1;
  min-width: 0;
}

.report-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: 22px;
  box-shadow: var(--shadow-sm);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
}

.card-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text);
}

.card-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: var(--radius-full);
  background: #F3F4F6;
  color: var(--color-text-secondary);
}

.card-badge.blue {
  background: var(--color-blue-light);
  color: var(--color-blue);
}

.card-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-left: auto;
}

/* 雷达图 */
.radar-card { min-height: 340px; }
.chart-container { width: 100%; height: 240px; }

/* 维度定性标签 */
.dim-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.dim-tag {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
}

.dim-label {
  color: var(--color-text-secondary);
  font-weight: 500;
}

.dim-level {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: var(--radius-full);
}

.dim-level.green { color: var(--color-green); background: var(--color-green-light); }
.dim-level.blue  { color: var(--color-blue);  background: var(--color-blue-light); }
.dim-level.amber { color: var(--color-amber);  background: #FFFBEB; border: 1px solid #FDE68A; }
.dim-level.red   { color: var(--color-red);    background: #FEF2F2; border: 1px solid #FECACA; }

/* 硬指标 */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

.stat-item {
  background: var(--color-bg);
  border-radius: var(--radius-md);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  position: relative;
}

.stat-item.warning {
  background: #FFFBEB;
  border: 1px solid #FDE68A;
}

.stat-val {
  font-size: 22px;
  font-weight: 800;
  color: var(--color-text);
  letter-spacing: -0.5px;
  line-height: 1.1;
}

.stat-unit {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-muted);
  margin-left: 2px;
}

.stat-label {
  font-size: 11.5px;
  color: var(--color-text-muted);
  font-weight: 500;
}

.stat-warn-tag {
  position: absolute;
  top: 10px;
  right: 10px;
  font-size: 10px;
  font-weight: 700;
  color: var(--color-amber);
  background: #FFFBEB;
  border: 1px solid #FDE68A;
  padding: 2px 6px;
  border-radius: var(--radius-full);
}

/* 口头禅 */
.filler-section { border-top: 1px solid var(--color-border-light); padding-top: 16px; }
.filler-title { font-size: 12px; font-weight: 600; color: var(--color-text-secondary); display: block; margin-bottom: 12px; }
.filler-list { display: flex; flex-direction: column; gap: 8px; }

.filler-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filler-word {
  font-size: 12px;
  color: var(--color-text-secondary);
  font-weight: 500;
  width: 80px;
  flex-shrink: 0;
}

.filler-bar-wrap {
  flex: 1;
  height: 6px;
  background: var(--color-border-light);
  border-radius: 3px;
  overflow: hidden;
}

.filler-bar {
  height: 100%;
  border-radius: 3px;
  background: var(--color-border);
  transition: width 1s ease;
}

.filler-bar.hot { background: #FCA5A5; }

.filler-count {
  font-size: 12px;
  color: var(--color-text-muted);
  width: 32px;
  text-align: right;
  flex-shrink: 0;
}

.filler-count.hot { color: var(--color-red); font-weight: 600; }

/* 练习目标卡片 */
.goal-card {
  border: 1.5px solid #DDD6FE;
  background: linear-gradient(135deg, #FAFAFA 0%, #F5F3FF 100%);
}

.goal-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}

.goal-icon { font-size: 22px; flex-shrink: 0; }

.goal-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text);
  display: block;
  margin-bottom: 3px;
}

.goal-subtitle {
  font-size: 12px;
  color: var(--color-text-muted);
}

.goal-level-wrap {
  margin-left: auto;
  flex-shrink: 0;
}

.goal-level-badge {
  font-size: 13px;
  font-weight: 700;
  padding: 5px 14px;
  border-radius: var(--radius-full);
}

.goal-level-badge.green { color: var(--color-green); background: var(--color-green-light); border: 1px solid #A7F3D0; }
.goal-level-badge.blue  { color: var(--color-blue);  background: var(--color-blue-light);  border: 1px solid #BFDBFE; }
.goal-level-badge.amber { color: #92400E; background: #FFFBEB; border: 1px solid #FDE68A; }
.goal-level-badge.red   { color: var(--color-red);   background: #FEF2F2; border: 1px solid #FECACA; }

.goal-feedback {
  font-size: 13.5px;
  color: var(--color-text-secondary);
  line-height: 1.7;
  background: white;
  border-radius: var(--radius-md);
  padding: 14px 16px;
  border: 1px solid #EDE9FE;
}

/* 时间分配 */
.time-bars { display: flex; flex-direction: column; gap: 12px; }

.time-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.time-label {
  font-size: 12.5px;
  color: var(--color-text-secondary);
  font-weight: 500;
  width: 64px;
  flex-shrink: 0;
}

.time-bar-wrap {
  flex: 1;
  height: 10px;
  background: var(--color-border-light);
  border-radius: 5px;
  overflow: hidden;
}

.time-bar-fill {
  height: 100%;
  border-radius: 5px;
  transition: width 1.2s cubic-bezier(0.22, 1, 0.36, 1);
}

.time-duration {
  font-size: 12px;
  color: var(--color-text-muted);
  width: 36px;
  text-align: right;
  flex-shrink: 0;
}

/* 问答类型 */
.qa-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px; }

.qa-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.qa-type {
  font-size: 12.5px;
  color: var(--color-text-secondary);
  font-weight: 500;
  width: 52px;
  flex-shrink: 0;
}

.qa-bar-wrap {
  flex: 1;
  height: 10px;
  background: var(--color-border-light);
  border-radius: 5px;
  overflow: hidden;
}

.qa-bar-fill {
  height: 100%;
  border-radius: 5px;
  border: 1.5px solid rgba(0,0,0,0.08);
  transition: width 1.2s cubic-bezier(0.22, 1, 0.36, 1);
}

.qa-count { font-size: 12px; color: var(--color-text-muted); width: 80px; text-align: right; flex-shrink: 0; }
.qa-pct { color: var(--color-text-muted); }

.qa-tip {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 10px 12px;
  background: #FFFBEB;
  border-radius: var(--radius-md);
  border: 1px solid #FDE68A;
  font-size: 12.5px;
  color: #92400E;
  line-height: 1.5;
}

.qa-tip-icon { font-size: 14px; flex-shrink: 0; }

/* 改进建议 */
.suggestions-body {
  font-size: 13.5px;
  color: var(--color-text-secondary);
  line-height: 1.8;
}

.suggestions-body :deep(strong) { color: var(--color-text); font-weight: 600; }
.suggestions-body :deep(.list-marker) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: var(--color-blue);
  color: white;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 700;
  margin-right: 4px;
}

/* 历史对比 */
.history-card {
  background: linear-gradient(135deg, #F0FDF4 0%, #ECFDF5 100%);
  border: 1.5px solid #A7F3D0;
}

.history-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.history-icon { font-size: 18px; }

.history-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text);
}

.history-badge {
  font-size: 11px;
  font-weight: 700;
  color: var(--color-green);
  background: white;
  border: 1px solid #A7F3D0;
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

.history-text {
  font-size: 13.5px;
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.history-text :deep(strong) { color: var(--color-green); font-weight: 700; }

/* 关键节点时间轴 */
.events-list { display: flex; flex-direction: column; gap: 0; }

.event-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border-light);
  position: relative;
}

.event-item:last-child { border-bottom: none; }

.event-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-border);
  flex-shrink: 0;
  margin-top: 4px;
}

.event-item.good .event-dot { background: var(--color-green); }
.event-item.warning .event-dot { background: var(--color-amber); }

.event-time {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  width: 42px;
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}

.event-text {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.event-item.good .event-text { color: #065F46; }
.event-item.warning .event-text { color: #92400E; }
</style>
