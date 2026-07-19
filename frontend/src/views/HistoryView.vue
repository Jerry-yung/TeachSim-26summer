<template>
  <div class="history-view">
    <div class="header">
      <h2>历史课堂</h2>
      <div ref="filterWrapRef" class="filter-wrap">
        <div class="toolbar">
          <input
            v-model.trim="filters.topic"
            class="input"
            type="text"
            placeholder="按课题关键词搜索"
            @keyup.enter="loadHistory"
          />
          <button class="date-btn" @click="openDatePicker('start_date', $event)">
            {{ filters.start_date || '起始日期' }}
          </button>
          <span class="to">至</span>
          <button class="date-btn" @click="openDatePicker('end_date', $event)">
            {{ filters.end_date || '终止日期' }}
          </button>
          <button class="refresh-btn" @click="loadHistory" :disabled="loading">
            {{ loading ? '加载中…' : '搜索' }}
          </button>
          <button class="reset-btn" @click="resetFilters" :disabled="loading">重置</button>
        </div>
        <div v-if="datePicker.open" class="calendar-panel" :style="calendarPanelStyle">
          <div class="calendar-head">
            <div class="calendar-title">
              选择{{ datePicker.field === 'start_date' ? '起始' : '终止' }}日期
            </div>
            <button class="close-btn" @click="closeDatePicker">关闭</button>
          </div>
          <div class="calendar-controls">
            <select v-model.number="datePicker.year" class="calendar-select">
              <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
            </select>
            <select v-model.number="datePicker.month" class="calendar-select">
              <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
            </select>
          </div>
          <div class="weekday-grid">
            <span v-for="w in weekdays" :key="w" class="weekday">{{ w }}</span>
          </div>
          <div class="day-grid">
            <button
              v-for="cell in calendarCells"
              :key="cell.key"
              class="day"
              :class="{
                placeholder: cell.placeholder,
                selected: cell.key === selectedDateForPicker,
                'has-history': !cell.placeholder && hasHistory(cell.key),
                'no-history': !cell.placeholder && !hasHistory(cell.key),
              }"
              :disabled="cell.placeholder"
              @click="pickDate(cell.key)"
            >
              {{ cell.day }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="!loading && !items.length" class="empty">
      暂无历史课堂记录
    </div>

    <div v-else class="list">
      <div v-for="item in items" :key="item.session_id" class="card">
        <div class="row top">
          <div class="main">
            <div class="title">{{ item.lesson_topic || '未命名课程' }}</div>
            <div class="meta">
              {{ item.subject || '通用' }} · {{ item.class_info || '未标注班级' }} · {{ formatTime(item.created_at) }}
            </div>
          </div>
          <div class="duration">时长 {{ item.duration_min || 0 }} 分钟</div>
        </div>
        <div class="overall">
          <span class="overall-label">overall</span>
          <div class="overall-text">{{ overallText(item) }}</div>
        </div>
        <div class="actions">
          <button class="link-btn" @click="viewReport(item.session_id)">查看报告</button>
          <button class="danger-btn" @click="removeSession(item.session_id)">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchHistorySessions,
  fetchHistorySessionDates,
  getCachedHistorySessions,
  deleteHistorySession,
} from '@/api/ai'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const items = ref([])
const availableDateSet = ref(new Set())
const filterWrapRef = ref(null)
const filters = ref({
  topic: '',
  start_date: '',
  end_date: '',
})
const weekdays = ['一', '二', '三', '四', '五', '六', '日']
const datePicker = ref({
  open: false,
  field: 'start_date',
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1,
  left: 0,
})

const yearOptions = computed(() => {
  const now = new Date().getFullYear()
  const years = []
  for (let y = now - 4; y <= now + 2; y += 1) years.push(y)
  return years
})

const selectedDateForPicker = computed(() => {
  const key = filters.value[datePicker.value.field]
  return key || ''
})
const calendarPanelStyle = computed(() => ({
  left: `${Math.max(0, datePicker.value.left)}px`,
}))

const calendarCells = computed(() => {
  const y = datePicker.value.year
  const m = datePicker.value.month
  const first = new Date(y, m - 1, 1)
  const firstWeekday = (first.getDay() + 6) % 7
  const daysInMonth = new Date(y, m, 0).getDate()
  const cells = []
  for (let i = 0; i < firstWeekday; i += 1) {
    cells.push({ key: `p-${i}`, day: '', placeholder: true })
  }
  for (let d = 1; d <= daysInMonth; d += 1) {
    const key = toDateKey(y, m, d)
    cells.push({ key, day: d, placeholder: false })
  }
  const tail = cells.length % 7 === 0 ? 0 : 7 - (cells.length % 7)
  for (let i = 0; i < tail; i += 1) {
    cells.push({ key: `t-${i}`, day: '', placeholder: true })
  }
  return cells
})

function formatTime(text) {
  if (!text) return '未知时间'
  const d = new Date(text)
  if (Number.isNaN(d.getTime())) return text
  return d.toLocaleString()
}

function overallText(item) {
  const text = String(item?.overall_desc || '').trim()
  if (text) return text
  return item?.overall_level || '未生成报告'
}

function toDateKey(year, month, day) {
  const mm = String(month).padStart(2, '0')
  const dd = String(day).padStart(2, '0')
  return `${year}-${mm}-${dd}`
}

function hasHistory(key) {
  return availableDateSet.value.has(key)
}

function openDatePicker(field, event) {
  datePicker.value.field = field
  const raw = filters.value[field]
  const basis = raw ? new Date(raw) : new Date()
  datePicker.value.year = basis.getFullYear()
  datePicker.value.month = basis.getMonth() + 1
  const wrapRect = filterWrapRef.value?.getBoundingClientRect()
  const btnRect = event?.currentTarget?.getBoundingClientRect?.()
  if (wrapRect && btnRect) {
    datePicker.value.left = btnRect.left - wrapRect.left
  } else {
    datePicker.value.left = 0
  }
  datePicker.value.open = true
  loadAvailableDates(items.value)
}

function closeDatePicker() {
  datePicker.value.open = false
}

function pickDate(key) {
  filters.value[datePicker.value.field] = key
  closeDatePicker()
}

function buildDateSetFromItems(rows) {
  const s = new Set()
  for (const row of rows || []) {
    const raw = row?.created_at
    if (!raw) continue
    const key = String(raw).slice(0, 10)
    if (/^\d{4}-\d{2}-\d{2}$/.test(key)) s.add(key)
  }
  return s
}

async function loadAvailableDates(seedItems = []) {
  const fallback = buildDateSetFromItems(seedItems)
  try {
    const res = await fetchHistorySessionDates({ topic: filters.value.topic })
    const next = new Set(Array.isArray(res?.dates) ? res.dates : [])
    for (const v of fallback) next.add(v)
    availableDateSet.value = next
  } catch {
    availableDateSet.value = fallback
  }
}

async function loadHistory() {
  loading.value = true
  error.value = ''
  try {
    const cached = getCachedHistorySessions({
      limit: 50,
      offset: 0,
      topic: filters.value.topic,
      start_date: filters.value.start_date,
      end_date: filters.value.end_date,
    })
    if (Array.isArray(cached?.items) && cached.items.length) {
      items.value = cached.items
    }
    const data = await fetchHistorySessions({
      limit: 50,
      offset: 0,
      topic: filters.value.topic,
      start_date: filters.value.start_date,
      end_date: filters.value.end_date,
    })
    items.value = Array.isArray(data?.items) ? data.items : []
    loadAvailableDates(items.value)
  } catch (e) {
    error.value = e?.message || '历史课堂加载失败'
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.value.topic = ''
  filters.value.start_date = ''
  filters.value.end_date = ''
  closeDatePicker()
  loadHistory()
}

function viewReport(sessionId) {
  router.push(`/report/${sessionId}`)
}

async function removeSession(sessionId) {
  const ok = window.confirm('确认删除该历史课堂？删除后不可恢复。')
  if (!ok) return
  try {
    await deleteHistorySession(sessionId)
    items.value = items.value.filter((x) => x.session_id !== sessionId)
  } catch (e) {
    window.alert(e?.message || '删除失败')
  }
}

function handleDocPointerDown(event) {
  if (!datePicker.value.open) return
  const root = filterWrapRef.value
  if (!root) return
  const target = event.target
  if (root.contains(target)) return
  closeDatePicker()
}

onMounted(() => {
  document.addEventListener('mousedown', handleDocPointerDown)
  loadHistory()
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleDocPointerDown)
})
</script>

<style scoped>
.history-view { padding: 20px 28px; color: #0f172a; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 12px; flex-wrap: wrap; }
.header h2 { margin: 0; font-size: 24px; color: #020617; font-weight: 800; }
.filter-wrap { position: relative; }
.toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.input { border: 1px solid #cbd5e1; background: #fff; color: #0f172a; border-radius: 10px; padding: 8px 10px; min-width: 220px; }
.date-btn { border: 1px solid #cbd5e1; background: #fff; color: #0f172a; border-radius: 10px; padding: 8px 12px; min-width: 126px; text-align: left; cursor: pointer; }
.to { color: #64748b; font-size: 12px; }
.refresh-btn { border: 1px solid #3b82f6; background: #3b82f6; color: #fff; border-radius: 10px; padding: 8px 12px; cursor: pointer; }
.reset-btn { border: 1px solid #cbd5e1; background: #fff; color: #475569; border-radius: 10px; padding: 8px 12px; cursor: pointer; }
.error { color: #f87171; margin: 8px 0; }
.empty { color: #64748b; margin-top: 24px; }
.calendar-panel { position: absolute; top: calc(100% + 8px); z-index: 40; width: 300px; max-width: calc(100vw - 60px); border: 1px solid #1e293b; border-radius: 14px; padding: 12px; background: #0f172a; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.2); }
.calendar-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.calendar-title { color: #e2e8f0; font-weight: 600; font-size: 13px; }
.close-btn { border: 1px solid #334155; background: transparent; color: #cbd5e1; border-radius: 8px; padding: 4px 8px; cursor: pointer; }
.calendar-controls { display: flex; gap: 8px; margin-bottom: 8px; }
.calendar-select { border: 1px solid #334155; background: #111827; color: #f8fafc; border-radius: 8px; padding: 6px 8px; }
.weekday-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 4px; }
.weekday { text-align: center; color: #94a3b8; font-size: 12px; }
.day-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
.day { border: none; background: transparent; border-radius: 999px; aspect-ratio: 1 / 1; text-align: center; cursor: pointer; font-size: 14px; }
.day.placeholder { cursor: default; opacity: 0; }
.day.has-history { color: #ffffff; font-weight: 700; }
.day.no-history { color: rgba(226, 232, 240, 0.4); }
.day.selected { background: #22c55e; color: #ffffff; font-weight: 700; }
.list { display: grid; gap: 14px; }
.card { border: 1px solid #dbe3ee; background: #f8fafc; border-radius: 14px; padding: 16px; box-shadow: 0 1px 0 #e5edf8; }
.row.top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.main { flex: 1 1 auto; min-width: 0; }
.title { font-size: 17px; font-weight: 700; color: #0f172a; line-height: 1.35; word-break: break-word; }
.meta { margin-top: 6px; color: #334155; font-size: 13px; word-break: break-word; }
.duration { flex: 0 0 auto; font-size: 13px; color: #1e293b; border: 1px solid #cbd5e1; background: #fff; border-radius: 999px; padding: 4px 10px; }
.overall { margin-top: 12px; padding: 10px 12px; border: 1px solid #d5dfeb; background: #ffffff; border-radius: 10px; }
.overall-label { display: inline-block; font-size: 11px; letter-spacing: 0.04em; color: #64748b; text-transform: uppercase; margin-bottom: 4px; }
.overall-text {
  color: #0f172a;
  font-size: 12px;
  line-height: 1.65;
  word-break: break-word;
  white-space: pre-wrap;
}
.actions { margin-top: 10px; display: flex; gap: 8px; }
.link-btn, .danger-btn { border-radius: 8px; padding: 6px 10px; cursor: pointer; border: 1px solid #cbd5e1; background: #fff; color: #1e293b; }
.danger-btn { border-color: #fecaca; color: #b91c1c; }
</style>

