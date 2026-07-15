<template>
  <div class="interview-view">

    <!-- Top bar: progress + exit -->
    <div class="interview-topbar">
      <button class="exit-btn" @click="router.push('/setup')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        退出
      </button>

      <div class="progress-wrap">
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: `${store.interviewProgress}%` }"></div>
        </div>
        <span class="progress-label">
          {{ Math.min(store.currentQuestionIndex + 1, store.totalQuestions) }} / {{ store.totalQuestions }}
        </span>
      </div>

      <div class="topbar-spacer"></div>
    </div>

    <!-- Main area -->
    <div class="interview-body">

      <!-- Completed state -->
      <Transition name="fade">
        <div v-if="store.isInterviewComplete" class="complete-card animate-fadeInUp">
          <div class="complete-icon">🎉</div>
          <h2 class="complete-title">配置完成！</h2>
          <p class="complete-desc">
            所有问题已回答，AI 已了解您的课堂需求。<br>
            即将进入虚拟课堂，祝您授课顺利！
          </p>
          <div class="complete-summary">
            <div v-for="(val, key) in answeredSummary" :key="key" class="summary-row">
              <span class="summary-key">{{ questionLabel(key) }}</span>
              <span class="summary-val">{{ formatAnswer(val) }}</span>
            </div>
          </div>
          <p v-if="enterError" class="enter-error">{{ enterError }}</p>
          <button class="enter-btn" :disabled="entering" @click="enterClassroom">
            {{ entering ? '课堂初始化中…' : '进入课堂' }}
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <line x1="5" y1="12" x2="19" y2="12" stroke-linecap="round"/>
              <polyline points="12 5 19 12 12 19" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>
      </Transition>

      <!-- Question card -->
      <Transition :name="transitionName" mode="out-in">
        <div
          v-if="!store.isInterviewComplete && store.currentQuestion"
          :key="store.currentQuestionIndex"
          class="question-card"
        >
          <!-- Step indicator -->
          <div class="question-meta">
            <span class="question-emoji">{{ store.currentQuestion.emoji }}</span>
            <span class="question-step">问题 {{ store.currentQuestionIndex + 1 }}</span>
            <span v-if="!store.currentQuestion.required" class="optional-badge">选填</span>
          </div>

          <!-- Question text -->
          <h2 class="question-text">{{ store.currentQuestion.label }}</h2>

          <!-- Hint -->
          <p v-if="store.currentQuestion.hint" class="question-hint-text">
            💡 {{ store.currentQuestion.hint }}
          </p>
          <p v-if="isMultiSelect" class="question-hint-text multi-hint">
            ✅ 本题支持多选，可点击多个选项后再确认
          </p>

          <!-- Options -->
          <div class="options-list">
            <button
              v-for="(opt, idx) in store.currentQuestion.options"
              :key="opt"
              class="option-btn"
              :class="{ selected: isOptionSelected(opt) }"
              @click="selectOption(opt)"
            >
              <span class="option-letter">{{ String.fromCharCode(65 + idx) }}</span>
              <span class="option-text">{{ opt }}</span>
              <span class="option-check">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                  <polyline points="20 6 9 17 4 12" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
            </button>
          </div>

          <!-- Navigation row -->
          <div class="nav-row">
            <button
              v-if="store.currentQuestionIndex > 0"
              class="nav-btn secondary"
              @click="store.goBack()"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="15 18 9 12 15 6" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              上一题
            </button>
            <div class="nav-spacer"></div>
            <button
              v-if="store.currentQuestion.skippable"
              class="nav-btn skip"
              @click="store.skipQuestion()"
            >
              跳过此题
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9 18 15 12 9 6" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
            <button
              v-if="isMultiSelect"
              class="nav-btn confirm"
              :disabled="!canConfirmMulti"
              @click="confirmMultiSelect"
            >
              确认并下一题
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9 18 15 12 9 6" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      </Transition>

      <!-- Teacher context hint (shown if filled) -->
      <div v-if="store.teacherContext && !store.isInterviewComplete" class="context-hint-bar">
        <span class="hint-icon">📝</span>
        <span class="hint-text">
          已读取您的描述，如有重复提问可直接跳过
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useLessonStore } from '@/stores/lessonStore.js'

const store = useLessonStore()
const router = useRouter()
const route = useRoute()

const selectedValue = ref(null)
const selectedValues = ref([])
const entering = ref(false)
const enterError = ref('')

const transitionName = computed(() =>
  store.interviewDirection === 'forward' ? 'slide-forward' : 'slide-back'
)

function selectOption(opt) {
  if (isMultiSelect.value) {
    if (selectedValues.value.includes(opt)) {
      selectedValues.value = selectedValues.value.filter((v) => v !== opt)
    } else {
      selectedValues.value = [...selectedValues.value, opt]
    }
    return
  }

  selectedValue.value = opt
  // Brief visual feedback before advancing
  setTimeout(() => {
    store.answerAndNext(store.currentQuestion.id, opt)
    selectedValue.value = null
  }, 260)
}

function isOptionSelected(opt) {
  return isMultiSelect.value ? selectedValues.value.includes(opt) : selectedValue.value === opt
}

const isMultiSelect = computed(() => !!store.currentQuestion?.allow_multiple)
const canConfirmMulti = computed(() => selectedValues.value.length > 0)

function confirmMultiSelect() {
  if (!isMultiSelect.value || !canConfirmMulti.value) return
  store.answerAndNext(store.currentQuestion.id, [...selectedValues.value])
  selectedValues.value = []
}

watch(
  () => store.currentQuestion?.id,
  (id) => {
    selectedValue.value = null
    selectedValues.value = []
    if (!id) return
    const existing = store.interviewAnswers[id]
    if (Array.isArray(existing)) {
      selectedValues.value = [...existing]
    } else if (existing) {
      selectedValue.value = existing
    }
  },
  { immediate: true },
)

async function enterClassroom() {
  if (entering.value) return
  enterError.value = ''
  entering.value = true
  try {
    const res = await store.bootstrapClassroomSession(String(route.params.sessionId || ''))
    router.push(`/classroom/${res.session_id}`)
  } catch (err) {
    enterError.value = err?.message || '课堂初始化失败'
  } finally {
    entering.value = false
  }
}

const answeredSummary = computed(() => store.interviewAnswers)

function questionLabel(id) {
  const q = store.interviewQuestions.find((q) => q.id === id)
  return q?.label ?? id
}

function formatAnswer(val) {
  if (Array.isArray(val)) return val.join('、')
  return val
}
</script>

<style scoped>
.interview-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
}

/* ── Top bar ─────────────────────────────────────────────────────────── */
.interview-topbar {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 14px 28px;
  background: var(--color-card);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.exit-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 6px 10px;
  border-radius: var(--radius-md);
  transition: all 0.15s;
  flex-shrink: 0;
}

.exit-btn:hover {
  background: var(--color-bg);
  color: var(--color-text-secondary);
}

.progress-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: 420px;
  margin: 0 auto;
}

.progress-track {
  flex: 1;
  height: 5px;
  background: var(--color-border);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-blue);
  border-radius: 3px;
  transition: width 0.4s cubic-bezier(0.22, 1, 0.36, 1);
}

.progress-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}

.topbar-spacer { width: 64px; flex-shrink: 0; }

/* ── Body ────────────────────────────────────────────────────────────── */
.interview-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px 80px;
  position: relative;
  overflow: hidden;
}

/* ── Question card ───────────────────────────────────────────────────── */
.question-card {
  width: 100%;
  max-width: 560px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 20px;
  padding: 36px 36px 28px;
  box-shadow: var(--shadow-md);
}

.question-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
}

.question-emoji {
  font-size: 24px;
}

.question-step {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.6px;
}

.optional-badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

.question-text {
  font-size: 21px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.4px;
  line-height: 1.35;
  margin-bottom: 10px;
}

.question-hint-text {
  font-size: 13px;
  color: var(--color-blue);
  background: var(--color-blue-light);
  padding: 8px 12px;
  border-radius: var(--radius-md);
  margin-bottom: 20px;
  line-height: 1.5;
}

.multi-hint {
  background: rgba(34, 197, 94, 0.1);
  color: #15803d;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 24px;
  margin-top: 16px;
}

.option-btn {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: var(--radius-lg);
  border: 1.5px solid var(--color-border);
  background: var(--color-card);
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
  position: relative;
  overflow: hidden;
}

.option-btn:hover {
  border-color: var(--color-blue);
  background: var(--color-blue-light);
}

.option-btn.selected {
  border-color: var(--color-blue);
  background: var(--color-blue);
}

.option-btn.selected .option-letter {
  background: rgba(255,255,255,0.2);
  color: white;
}

.option-btn.selected .option-text {
  color: white;
  font-weight: 600;
}

.option-btn.selected .option-check {
  opacity: 1;
  color: white;
}

.option-letter {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  background: var(--color-bg);
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s;
}

.option-text {
  flex: 1;
  font-size: 14px;
  color: var(--color-text-secondary);
  font-weight: 500;
  line-height: 1.4;
  transition: all 0.15s;
}

.option-check {
  opacity: 0;
  flex-shrink: 0;
  transition: opacity 0.15s;
}

/* ── Navigation ──────────────────────────────────────────────────────── */
.nav-row {
  display: flex;
  align-items: center;
  padding-top: 4px;
  border-top: 1px solid var(--color-border-light);
}

.nav-spacer { flex: 1; }

.nav-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 7px 12px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  border: none;
  background: none;
}

.nav-btn.secondary {
  color: var(--color-text-muted);
}

.nav-btn.secondary:hover {
  background: var(--color-bg);
  color: var(--color-text-secondary);
}

.nav-btn.skip {
  color: var(--color-text-muted);
}

.nav-btn.skip:hover {
  color: var(--color-text-secondary);
  background: var(--color-bg);
}

.nav-btn.confirm {
  color: #2563eb;
  background: rgba(37, 99, 235, 0.1);
  margin-left: 8px;
}

.nav-btn.confirm:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.nav-btn.confirm:not(:disabled):hover {
  background: rgba(37, 99, 235, 0.18);
}

/* ── Context hint bar ────────────────────────────────────────────────── */
.context-hint-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 20px;
  padding: 9px 16px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  font-size: 12.5px;
  color: var(--color-text-muted);
}

.hint-icon { font-size: 14px; }

/* ── Complete card ───────────────────────────────────────────────────── */
.complete-card {
  width: 100%;
  max-width: 500px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 20px;
  padding: 40px 36px 32px;
  box-shadow: var(--shadow-md);
  text-align: center;
}

.complete-icon { font-size: 48px; margin-bottom: 16px; }

.complete-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.4px;
  margin-bottom: 8px;
}

.complete-desc {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: 24px;
}

.complete-summary {
  background: var(--color-bg);
  border-radius: var(--radius-lg);
  padding: 16px;
  margin-bottom: 24px;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.summary-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.summary-key {
  font-size: 11.5px;
  color: var(--color-text-muted);
  font-weight: 600;
  min-width: 130px;
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.summary-val {
  font-size: 13px;
  color: var(--color-text);
  font-weight: 500;
}

.enter-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 13px 28px;
  background: var(--color-accent);
  color: white;
  border-radius: var(--radius-md);
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  letter-spacing: -0.2px;
}

.enter-btn:hover:not(:disabled) {
  opacity: 0.88;
  transform: translateY(-1px);
}

.enter-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.enter-error {
  margin-bottom: 12px;
  color: #dc2626;
  font-size: 12.5px;
}

/* ── Slide transitions ───────────────────────────────────────────────── */
.slide-forward-enter-active,
.slide-forward-leave-active,
.slide-back-enter-active,
.slide-back-leave-active {
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}

.slide-forward-enter-from {
  opacity: 0;
  transform: translateX(48px);
}

.slide-forward-leave-to {
  opacity: 0;
  transform: translateX(-48px);
}

.slide-back-enter-from {
  opacity: 0;
  transform: translateX(-48px);
}

.slide-back-leave-to {
  opacity: 0;
  transform: translateX(48px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.35s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fadeInUp {
  animation: fadeInUp 0.4s ease both;
}
</style>
