<template>
  <div class="classroom-root" :class="{ 'has-ppt': hasPptMode }">

    <!-- ══ HEADER BAR ══ -->
    <div class="hdr">
      <router-link to="/setup" class="hdr-btn hdr-back">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
        返回配置
      </router-link>

      <div class="hdr-center">
        <span class="mode-pill" :class="modeCls">{{ modeLabel }}</span>
        <span class="timer" :class="{ overtime: isOvertime }">{{ timerStr }}</span>
        <span v-if="durationWarnText" class="duration-warn">{{ durationWarnText }}</span>
      </div>

      <button class="hdr-btn hdr-end" @click="endClass">
        结束课程
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </button>
    </div>

    <!-- ══ MAIN AREA ══ -->
    <div class="main-area" :class="{ 'with-ppt': hasPptMode }">
      <div class="left-stack">
        <div v-if="hasPptMode" class="ppt-panel in-main">
          <div class="ppt-bar">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/>
              <line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
            {{ pptDisplayName }}
            <span class="ppt-pages">第 {{ pptPage }} / {{ pptTotal }} 页</span>
            <button class="ppt-nav" @click="pptPage = Math.max(1, pptPage - 1)">‹</button>
            <button class="ppt-nav" @click="pptPage = Math.min(pptTotal, pptPage + 1)">›</button>
          </div>
          <div ref="pptViewWrapRef" class="ppt-view">
            <template v-if="pptPreviewUrl">
              <canvas ref="pdfCanvasRef" class="ppt-canvas" />
              <p v-if="pdfRenderError" class="ppt-pdf-error">{{ pdfRenderError }}</p>
            </template>
            <div v-else class="ppt-placeholder">
              <p>📊 {{ pptDisplayName }}</p>
              <p class="ppt-hint">{{ pptPreviewNotice }}</p>
              <p class="ppt-hint">{{ currentPptTextDisplay }}</p>
            </div>
          </div>
        </div>

      <!-- LEFT: transcript panel -->
      <div class="transcript-panel" :class="{ compact: hasPptMode }">
        <div class="panel-title">
          <span class="dot" :class="{ active: isRecording }"/>
          {{ isRecording ? '讯飞实时转写中…' : '教师语音' }}
        </div>

        <div class="transcript-scroll" ref="scrollEl">
          <p v-if="!transcript && !interimText" class="empty-hint">
            点击下方「开始授课」开启麦克风，语音将实时转写显示在此处。
          </p>
          <span class="final-text">{{ transcript }}</span>
          <span class="interim-text">{{ interimText }}</span>
        </div>

        <!-- no speech recognition support warning -->
        <div v-if="!asrSupported" class="warn-box">
          ⚠️ 当前环境不支持讯飞 WebSocket 语音转写，请使用 HTTPS 下的 Chrome/Edge。
        </div>
        <div v-if="micError" class="warn-box err-box">{{ micError }}</div>
        <div v-if="pipelineError" class="warn-box err-box">{{ pipelineError }}</div>
      </div>
      </div>

      <!-- RIGHT: agent response panel -->
      <div class="response-panel">
        <div class="panel-title">学生响应</div>

        <transition name="slide-up">
          <div v-if="currentResp" class="resp-card" :style="{ '--ac': agentColor(currentResp.student_type) }">
            <div class="resp-agent">
              <span class="resp-dot"/>
              {{ currentResp.student_name || agentLabel(currentResp.student_type) }}
            </div>
            <div class="resp-text">{{ currentResp.reply_text }}</div>
          </div>
          <div v-else class="resp-empty">
            <div class="resp-empty-icon">🎓</div>
            <p>学生正在聆听…</p>
          </div>
        </transition>

        <div v-if="questioningMergeHint" class="merge-hint">
          {{ questioningMergeHint }}
        </div>

        <div v-if="candidateEvents.length" class="candidate-wrap">
          <div class="log-title">可选回答（老师点名后触发）</div>
          <div class="candidate-list">
            <button
              v-for="(evt, idx) in candidateEvents"
              :key="`${evt.student_id || evt.student_type}-${idx}`"
              class="candidate-btn"
              @click="triggerCandidate(evt)"
            >
              {{ evt.student_name || agentLabel(evt.student_type) }}（{{ academicLabel(evt.academic_type) }}）：
              {{ evt.reply_text }}
            </button>
          </div>
        </div>

        <!-- session log -->
        <div v-if="sessionLog.length" class="session-log">
          <div class="log-title">本节对话记录</div>
          <div class="log-item" v-for="(entry, i) in sessionLog" :key="i">
            <span class="log-who" :style="{ color: agentColor(entry.student_type) }">
              {{ entry.student_name || agentLabel(entry.student_type) }}
            </span>
            <span class="log-text">{{ entry.reply_text }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ══ STUDENT STAGE ══ -->
    <div class="student-stage" :class="{ 'with-ppt': hasPptMode }">
      <StudentFigure
        v-for="s in students"
        :key="s.id"
        :behavior="s.behavior"
        :color="s.color"
        :name="s.name"
        :active="activeStudent === s.id"
        :standing="!!poseByStudent[s.id]?.standing"
        :hand-raised="!!poseByStudent[s.id]?.handRaised"
        :sleeping="!!poseByStudent[s.id]?.sleeping"
        :whisper-side="poseByStudent[s.id]?.whisperSide || 'none'"
        :idle-video-src="s.id === 'student_xm' ? xiaomingIdleVideoSrc : ''"
      />
    </div>

    <!-- ══ VISUAL: 隐藏摄像头预览 + canvas ══ -->
    <video ref="visualVideoRef" style="display:none" playsinline muted autoplay></video>
    <canvas ref="visualCanvasRef" style="display:none"></canvas>

    <!-- ══ 教姿分析同意弹窗 ══ -->
    <transition name="fade">
      <div v-if="showVisualConsentModal" class="visual-consent-overlay" @click.self="onVisualConsentDecline">
        <div class="visual-consent-modal">
          <div class="vcm-icon">📷</div>
          <h3 class="vcm-title">开启教姿教态分析</h3>
          <p class="vcm-body">
            本功能将通过摄像头采集您在授课时的肢体语言、手势与表情，
            借助 AI 模型在课后生成<strong>教姿教态分析报告</strong>，帮助您优化教学呈现。
          </p>
          <ul class="vcm-list">
            <li>每 15 秒采样约 3 帧图像及 2-3 秒短片段</li>
            <li>数据仅用于本课程报告，保留 30 天后自动删除</li>
            <li>不会录制全程完整视频，不会上传至第三方</li>
            <li>您可随时在报告中关闭此功能</li>
          </ul>
          <p v-if="!visualCameraSupported" class="vcm-warning">
            当前浏览器环境不支持摄像头（请使用 localhost 或 HTTPS 访问）。
          </p>
          <div class="vcm-actions">
            <button
              class="vcm-btn vcm-agree"
              :disabled="!visualCameraSupported"
              @click="onVisualConsentAgree"
            >同意并开启摄像头</button>
            <button class="vcm-btn vcm-decline" @click="onVisualConsentDecline">暂不开启</button>
          </div>
        </div>
      </div>
    </transition>

    <!-- ══ CONTROL BAR ══ -->
    <div class="ctrl-bar">
      <button
        class="mic-btn"
        :class="{ recording: isRecording }"
        @click="toggleRecording"
        :disabled="!asrSupported"
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="23"/>
          <line x1="8"  y1="23" x2="16" y2="23"/>
        </svg>
        <span>{{ isRecording ? '暂停授课' : '开始授课' }}</span>
        <span v-if="isRecording" class="rec-pulse"/>
      </button>
      <div class="ctrl-hint">
        {{ isRecording ? '正在实时转写您的语音 · 学生将适时响应' : '准备好后点击开始授课' }}
        <span v-if="visualEnabled" class="visual-on-badge">教姿分析已开启</span>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, watch, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLessonStore } from '@/stores/lessonStore'
import {
  postInclassUtterance,
  fetchStudentState,
  postInclassSegment,
  postStudentReply,
  restartClassroomSession,
  fetchLessonPptPreview,
} from '@/api/ai'
import StudentFigure from '@/components/classroom/StudentFigure.vue'
import { XfyunASRClient, isXfyunSupported } from '@/api/xfyunAsr'
import { isMinimaxPlaying, minimaxSpeak, stopMinimaxPlayback } from '@/api/minimaxTts.js'
import { getXiaomingIdleVideoSrc } from '@/config/studentMedia'
import {
  loadPptPdfDocument,
  renderPptPdfPage,
  invalidatePptPdfCache,
} from '@/utils/pptPdf.js'
import { postVisualObservation } from '@/api/visual'

const router  = useRouter()
const route   = useRoute()
const store   = useLessonStore()
const currentSessionId = computed(() => String(route.params.sessionId || store.sessionId || ''))

function isReloadNavigation() {
  if (typeof window === 'undefined') return false
  const nav = window.performance?.getEntriesByType?.('navigation')?.[0]
  if (nav && nav.type) return nav.type === 'reload'
  return window.performance?.navigation?.type === 1
}

async function recoverSessionContextIfNeeded() {
  const routeSessionId = currentSessionId.value
  if (!routeSessionId) return
  if (typeof history !== 'undefined' && history.state?.fromInterview) {
    const nextState = { ...(history.state || {}), fromInterview: false }
    history.replaceState(nextState, '')
    return
  }
  if (!isReloadNavigation()) return
  try {
    const result = await restartClassroomSession(routeSessionId)
    if (!result?.session_id) return
    store.sessionId = result.session_id
    store.lessonId = result.lesson_id || store.lessonId
    if (result.session_id !== routeSessionId) {
      window.location.replace(`/classroom/${result.session_id}`)
    }
  } catch (err) {
    console.warn('[Classroom] 会话上下文恢复失败：', err?.message || err)
  }
}

// ── Students cast ──
const STUDENT_BASE_CAST = [
  { id: 'student_xm', name: '小明', color: '#A855F7', behavior: 'writing' },
  { id: 'student_xw', name: '小红', color: '#22D3EE', behavior: 'dreaming' },
  { id: 'student_xw2', name: '小王', color: '#60A5FA', behavior: 'writing' },
  { id: 'student_xl', name: '小乐', color: '#34D399', behavior: 'whisper-left' },
]
const students = ref(STUDENT_BASE_CAST.map((s) => ({ ...s })))

const xiaomingIdleVideoSrc = computed(() => getXiaomingIdleVideoSrc())

// ── Voice state ──
const asrSupported  = ref(isXfyunSupported())
const isRecording   = ref(false)
const transcript    = ref('')
const interimText   = ref('')
let interimCommitTimer = null
const scrollEl      = ref(null)
const micError      = ref('')   // permission / unsupported error message
const pipelineError = ref('')

// ── Supervisor / Agent state ──
const currentResp   = ref(null)
const activeStudent = ref(null)
const sessionLog    = ref([])
const chatHistory   = ref([])
const candidateEvents = ref([])
const candidatePool = ref({})
const poseByStudent = ref({})
const latestStateDigestMap = ref({})
const segmentEvalResults = ref([])
const supervisorQueue = []
let supervisorBusy = false
let sentenceBuffer = ''
let clearRespTimer = null
let clearPipelineErrorTimer = null
/** 递增以区分被 cancel 或新发言打断的语音会话 */
let speechGeneration = 0
let browserSpeechReject = null
const latestQuestioningEvents = ref([])
const pendingDeferredRound = ref(null)
const questioningBundle = ref({
  round_id: null,
  items: [],
  merged_text: '',
  question_count: 0,
  locked: false,
})
const activeDisciplineEvent = ref(null) // { student_id, action, started_at }
const lastTeacherSentence = ref(null)
const lastStudentSpeechAtMs = ref(0)
const recentTeacherUploadKeys = []
const TEACHER_DUPLICATE_WINDOW_MS = 4000
const recentAsrSentenceKeys = []
const ASR_SENTENCE_DUPLICATE_WINDOW_MS = 5000
const recentPointingReplyKeys = []
const POINTING_REPLY_DUPLICATE_WINDOW_MS = 6000
const QUESTIONING_HAND_DELAY_MS = 6000
const ENABLE_MOCK_QUESTIONING_FALLBACK = false
let questioningHandsTimer = null
let asrMuteUntilMs = 0

// ── Segment (send to backend) ──
const NO_PPT_SEGMENT_WINDOW_SEC = 30
let segmentSeq = 1
let currentSegment = null

// ── Timer ──
const elapsedSec    = ref(0)
let timerInterval   = null
let disciplineTickTimer = null
let lastDisciplineTickAtMs = 0
let lastDisciplineTriggeredAtMs = 0
const hasShownDurationWarn = ref(false)
const timerStr = computed(() => {
  const m = Math.floor(elapsedSec.value / 60).toString().padStart(2, '0')
  const s = (elapsedSec.value % 60).toString().padStart(2, '0')
  return `${m}:${s}`
})
const targetDurationSec = computed(() => {
  const raw = String(store.interviewAnswers?.duration || '').trim()
  if (!raw) return null
  const m = raw.match(/(\d+(?:\.\d+)?)/)
  if (!m) return null
  const minutes = Number(m[1])
  if (!Number.isFinite(minutes) || minutes <= 0) return null
  return Math.round(minutes * 60)
})
const remainingSecToTarget = computed(() => {
  if (!targetDurationSec.value) return null
  return targetDurationSec.value - elapsedSec.value
})
const isOvertime = computed(() => {
  if (!targetDurationSec.value) return false
  return elapsedSec.value > targetDurationSec.value
})
const durationWarnText = computed(() => {
  if (!targetDurationSec.value) return ''
  const remaining = remainingSecToTarget.value
  if (remaining === null) return ''
  if (remaining > 0 && remaining <= 60) {
    return `距设定时长还有 ${remaining}s`
  }
  if (remaining <= 0) return '已超时'
  return ''
})

// ── Mode badge ──
// 优先使用内存里的 File 对象；刷新后 File 丢失则回退到持久化的布尔标志。
const modeLabel = computed(() => {
  const hasLesson = !!store.uploadedLesson || store.hadLessonFile
  const hasPPT    = hasPptMode.value || store.hadPptFile
  if (hasLesson && hasPPT) return '教案 + PPT 模式'
  if (hasLesson)            return '教案模式'
  if (hasPPT)               return 'PPT 模式'
  return '自由模式'
})
const modeCls = computed(() => {
  const hasLesson = !!store.uploadedLesson || store.hadLessonFile
  const hasPPT    = hasPptMode.value || store.hadPptFile
  if (hasLesson && hasPPT) return 'mode-full'
  if (hasLesson || hasPPT)  return 'mode-partial'
  return 'mode-free'
})

function compactChatHistory() {
  return chatHistory.value.map((item) => ({
    current_timestamp: item.current_timestamp,
    role: item.role,
    content: item.content,
    called_student_id: item.called_student_id,
  }))
}

// ── PPT paging (records for agent context) ──
const pptPage  = ref(1)
const pptTotal = ref(12)
const pptPreviewUrl = ref('')
const pptPreviewNotice = ref('正在准备课件预览…')
const hasPptMode = ref(Boolean(store.uploadedPPT))
const inferredPptName = ref('')
const pdfCanvasRef = ref(null)
const pptViewWrapRef = ref(null)
const pdfRenderError = ref('')
let pdfPaintSeq = 0
let pdfResizeObserver = null
let pptPaintDebounceTimer = null
let pptPreviewRequestToken = 0
const pptDisplayName = computed(() => {
  const uploadedName = String(store.uploadedPPT?.name || '').trim()
  if (uploadedName) return uploadedName
  const inferred = String(inferredPptName.value || '').trim()
  if (inferred) return inferred
  return '课件预览'
})
async function paintPptPdfCanvas() {
  const url = String(pptPreviewUrl.value || '').trim()
  if (!url || !pdfCanvasRef.value) return
  const seq = ++pdfPaintSeq
  pdfRenderError.value = ''
  try {
    const wrap = pptViewWrapRef.value
    let maxW = wrap?.clientWidth ? Math.max(80, wrap.clientWidth - 12) : 720
    let maxH = wrap?.clientHeight ? Math.max(60, wrap.clientHeight - 8) : 480
    if (wrap && wrap.clientHeight < 40) {
      await new Promise((r) => requestAnimationFrame(r))
      if (seq !== pdfPaintSeq) return
      maxW = wrap.clientWidth ? Math.max(80, wrap.clientWidth - 12) : maxW
      maxH = wrap.clientHeight ? Math.max(60, wrap.clientHeight - 8) : maxH
    }
    const doc = await loadPptPdfDocument(url)
    if (seq !== pdfPaintSeq) return
    const nPages = Math.max(1, Number(doc.numPages) || 1)
    if (pptTotal.value !== nPages) pptTotal.value = nPages
    if (pptPage.value > nPages) pptPage.value = nPages
    await renderPptPdfPage(doc, pptPage.value, pdfCanvasRef.value, maxW, maxH)
  } catch (e) {
    if (seq !== pdfPaintSeq) return
    pdfRenderError.value = e?.message || '课件 PDF 渲染失败'
  }
}
function schedulePaintPptPdf() {
  clearTimeout(pptPaintDebounceTimer)
  pptPaintDebounceTimer = setTimeout(() => {
    pptPaintDebounceTimer = null
    void paintPptPdfCanvas()
  }, 80)
}

async function loadPptPreview() {
  const requestToken = ++pptPreviewRequestToken
  const file = store.uploadedPPT
  const lessonId = String(store.lessonId || '').trim()
  const hasLocalFile = Boolean(file)
  if (String(pptPreviewUrl.value || '').startsWith('blob:')) {
    invalidatePptPdfCache()
    URL.revokeObjectURL(pptPreviewUrl.value)
  }
  pptPreviewUrl.value = ''
  if (file?.name) {
    inferredPptName.value = String(file.name)
  }
  // 只有本次课堂真正上传/曾上传过 PPT 时才开启 PPT 模式；
  // lessonId 存在不代表有 PPT（仅上传教案也会产生 lessonId），需同时检查 hadPptFile。
  hasPptMode.value = hasLocalFile || (Boolean(lessonId) && store.hadPptFile)
  if (!file) {
    pptPreviewNotice.value = lessonId ? '正在读取已保存课件预览…' : '当前未上传课件文件'
  }
  if (!lessonId) {
    // fallback: local pdf can still preview even if lessonId is unavailable
    if (file && (file.type === 'application/pdf' || /\.pdf$/i.test(file.name || ''))) {
      pptPreviewUrl.value = URL.createObjectURL(file)
      hasPptMode.value = true
      pptPreviewNotice.value = '已加载本地 PDF 预览'
      return
    }
    if (!file) hasPptMode.value = false
    pptPreviewNotice.value = '课堂会话尚未初始化，暂无法加载预览'
    return
  }
  try {
    const maxAttempts = 15
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      if (requestToken !== pptPreviewRequestToken) return
      const data = await fetchLessonPptPreview(lessonId)
      const message = String(data?.message || '')
      const sourceMissing = message.includes('未找到可预览课件文件')
      pptTotal.value = Math.max(1, Number(data?.page_count || pptTotal.value || 1))
      if (pptPage.value > pptTotal.value) {
        pptPage.value = pptTotal.value
      }

      hasPptMode.value = hasLocalFile || !sourceMissing

      if (data?.ready && data?.preview_url) {
        const baseUrl = String(data.preview_url || '')
        const sep = baseUrl.includes('?') ? '&' : '?'
        pptPreviewUrl.value = `${baseUrl}${sep}t=${Date.now()}`
        pptPreviewNotice.value = '课件预览已就绪'
        return
      }

      if (file && (file.type === 'application/pdf' || /\.pdf$/i.test(file.name || ''))) {
        pptPreviewUrl.value = URL.createObjectURL(file)
        hasPptMode.value = true
        pptPreviewNotice.value = message || '已回退到本地 PDF 预览'
        return
      }

      const baseNotice = message || '课件预览尚未就绪'
      if (attempt < maxAttempts && !sourceMissing) {
        pptPreviewNotice.value = `${baseNotice}（自动重试 ${attempt}/${maxAttempts}）`
        await new Promise((resolve) => setTimeout(resolve, 2000))
        continue
      }
      pptPreviewNotice.value = baseNotice
      return
    }
  } catch (err) {
    if (file && (file.type === 'application/pdf' || /\.pdf$/i.test(file.name || ''))) {
      pptPreviewUrl.value = URL.createObjectURL(file)
      hasPptMode.value = true
      pptPreviewNotice.value = '后端预览失败，已回退本地 PDF 预览'
      return
    }
    if (!lessonId && !file) hasPptMode.value = false
    pptPreviewNotice.value = '后端预览加载失败，请稍后重试'
  }
}
watch(pptPage, async (newPage, oldPage) => {
  if (!hasPptMode.value || newPage === oldPage) return
  if (isRecording.value && currentSegment) {
    await flushCurrentSegment('ppt_page_switch')
  }
  startNewSegment()
})
watch(
  [pptPreviewUrl, pptPage],
  async () => {
    if (!pptPreviewUrl.value) return
    await nextTick()
    schedulePaintPptPdf()
  },
  { flush: 'post' },
)
watch(
  pptViewWrapRef,
  (el) => {
    pdfResizeObserver?.disconnect()
    pdfResizeObserver = null
    if (!el || typeof ResizeObserver === 'undefined') return
    pdfResizeObserver = new ResizeObserver(() => {
      if (pptPreviewUrl.value) schedulePaintPptPdf()
    })
    pdfResizeObserver.observe(el)
  },
  { flush: 'post' },
)
watch(
  () => [store.uploadedPPT, store.lessonId, store.sessionId],
  () => { loadPptPreview() },
  { immediate: true }
)
watch(
  () => [isRecording.value, remainingSecToTarget.value],
  () => {
    if (!isRecording.value) return
    const remaining = remainingSecToTarget.value
    if (remaining === null) return
    if (remaining <= 60 && remaining > 0 && !hasShownDurationWarn.value) {
      hasShownDurationWarn.value = true
      pipelineError.value = `⏰ 距离设定课堂时长还有 ${remaining} 秒，课堂不会自动结束。`
      clearTimeout(clearPipelineErrorTimer)
      clearPipelineErrorTimer = setTimeout(() => {
        pipelineError.value = ''
      }, 5000)
    }
    if (remaining > 60) {
      hasShownDurationWarn.value = false
    }
  },
)

// ── Agent helpers ──
const AGENT_MAP = {
  xueyou:        { label: '学优生',         color: '#22D3EE' },
  gangjing:      { label: '学优生 · 小精', color: '#A855F7' },
  xuekun:        { label: '学困生 · 小困', color: '#60A5FA' },
  sleepy:        { label: '瞌睡生 · 小眠', color: '#94A3B8' },
  whisper:       { label: '小悄悄 · 小语', color: '#34D399' },
  default:       { label: '学生',           color: '#22D3EE' },
}
function agentLabel(type) { return (AGENT_MAP[type] || AGENT_MAP.default).label }
function agentColor(type) { return (AGENT_MAP[type] || AGENT_MAP.default).color }
function academicLabel(type) {
  if (type === 'xueyou') return '学优'
  if (type === 'xuekun') return '学困'
  if (type === 'gangjing') return '杠精'
  return '未分层'
}

// Map agent type → student id for animation activation
const AGENT_TO_STUDENT = {
  xueyou: 'student_xm',
  gangjing: 'student_xw',
  xuekun: 'student_xw2',
  sleepy: 'student_xw2',
  whisper: 'student_xl',
}

function resolveStudentIdForEvent(eventObj) {
  if (eventObj?.student_id) return eventObj.student_id
  return AGENT_TO_STUDENT[eventObj?.student_type] || null
}

function initPoseState() {
  const next = {}
  for (const s of students.value) {
    next[s.id] = { standing: false, handRaised: false, sleeping: false, whisperSide: 'none' }
  }
  poseByStudent.value = next
}

function clearAllHands() {
  const next = { ...poseByStudent.value }
  for (const sid of Object.keys(next)) {
    next[sid] = { ...next[sid], handRaised: false }
  }
  poseByStudent.value = next
}

function applyRaisedHands(ids = []) {
  clearAllHands()
  if (!Array.isArray(ids)) return
  const next = { ...poseByStudent.value }
  for (const sid of ids) {
    if (!next[sid]) continue
    next[sid] = { ...next[sid], handRaised: true }
  }
  poseByStudent.value = next
}

function setStandingStudent(studentId) {
  const next = { ...poseByStudent.value }
  for (const sid of Object.keys(next)) {
    next[sid] = { ...next[sid], standing: sid === studentId }
    if (sid === studentId) next[sid].handRaised = false
  }
  poseByStudent.value = next
}

function clearStanding() {
  const next = { ...poseByStudent.value }
  for (const sid of Object.keys(next)) {
    next[sid] = { ...next[sid], standing: false }
  }
  poseByStudent.value = next
}

function updateDigestMap(digest) {
  const m = {}
  if (Array.isArray(digest)) {
    for (const item of digest) {
      if (!item?.student_id) continue
      m[item.student_id] = {
        student_id: item.student_id,
        student_type: item.student_type,
        is_hand_raised: Boolean(item.is_hand_raised),
      }
    }
  }
  latestStateDigestMap.value = m
}

function isDeferredDialogState(dialogState) {
  return dialogState === 'questioning' || dialogState === 'ambiguous' || dialogState === 'misstatement'
}

function clearDeferredRound(clearHands = true) {
  if (questioningHandsTimer) {
    clearTimeout(questioningHandsTimer)
    questioningHandsTimer = null
  }
  pendingDeferredRound.value = null
  latestQuestioningEvents.value = []
  questioningBundle.value = {
    round_id: null,
    items: [],
    merged_text: '',
    question_count: 0,
    locked: false,
  }
  candidatePool.value = {}
  candidateEvents.value = []
  if (clearHands) clearAllHands()
}

function replaceDeferredRound(nextRound) {
  const preserveQuestioningBundle = nextRound?.dialog_state === 'questioning'
  if (questioningHandsTimer) {
    clearTimeout(questioningHandsTimer)
    questioningHandsTimer = null
  }
  pendingDeferredRound.value = null
  latestQuestioningEvents.value = []
  candidatePool.value = {}
  candidateEvents.value = []
  clearAllHands()
  if (!preserveQuestioningBundle) {
    questioningBundle.value = {
      round_id: null,
      items: [],
      merged_text: '',
      question_count: 0,
      locked: false,
    }
  }
  pendingDeferredRound.value = nextRound
  const ids = []
  if (Array.isArray(nextRound?.raised_hand_student_ids) && nextRound.raised_hand_student_ids.length) {
    ids.push(...nextRound.raised_hand_student_ids)
  } else if (nextRound?.preset_for_student_id) {
    ids.push(nextRound.preset_for_student_id)
  }
  if (nextRound?.dialog_state === 'questioning') {
    // questioning 延迟 3s 出手势：3s 内新 questioning 会覆盖旧的一轮
    questioningHandsTimer = setTimeout(() => {
      const activeRound = pendingDeferredRound.value
      if (!activeRound || activeRound.roundId !== nextRound.roundId) return
      applyRaisedHands(ids)
      pendingDeferredRound.value = {
        ...activeRound,
        hands_applied_ms: Date.now(),
        bundle_locked: true,
      }
      questioningBundle.value = {
        ...questioningBundle.value,
        locked: true,
      }
      questioningHandsTimer = null
    }, QUESTIONING_HAND_DELAY_MS)
    return
  }
  applyRaisedHands(ids)
}

function appendQuestioningBundleFromTask(task, roundId) {
  if (questioningBundle.value?.locked) return
  const text = String(task?.content || '').trim()
  if (!text) return
  const item = {
    text,
    current_timestamp: task?.current_timestamp || '',
    class_elapsed_sec: Number.isFinite(task?.class_elapsed_sec) ? task.class_elapsed_sec : null,
  }
  const current = questioningBundle.value
  const keep =
    current.question_count > 0
    && pendingDeferredRound.value?.dialog_state === 'questioning'
  const items = keep ? [...current.items] : []
  const key = `${item.text}__${item.class_elapsed_sec ?? ''}`
  const exists = items.some((x) => `${x.text}__${x.class_elapsed_sec ?? ''}` === key)
  if (!exists) items.push(item)
  questioningBundle.value = {
    round_id: roundId,
    items,
    merged_text: items.map((x, idx) => `问题${idx + 1}：${x.text}`).join('\n'),
    question_count: items.length,
    locked: false,
  }
}

function getDigestState(studentId) {
  if (!studentId) return null
  const one = latestStateDigestMap.value[studentId]
  return one || null
}

function clearAllDisciplinePoses() {
  const next = { ...poseByStudent.value }
  for (const sid of Object.keys(next)) {
    next[sid] = { ...next[sid], sleeping: false, whisperSide: 'none' }
  }
  poseByStudent.value = next
}

function applyDisciplinePose(studentId, action) {
  clearAllDisciplinePoses()
  const next = { ...poseByStudent.value }
  if (!next[studentId]) return
  if (action === 'sleep') {
    next[studentId] = { ...next[studentId], sleeping: true, whisperSide: 'none', handRaised: false }
  } else {
    const side = Math.random() < 0.5 ? 'left' : 'right'
    next[studentId] = { ...next[studentId], sleeping: false, whisperSide: side, handRaised: false }
  }
  poseByStudent.value = next
}

function isStudentSpeakingNow() {
  const speakingApi = Boolean(window?.speechSynthesis?.speaking)
  return speakingApi || isMinimaxPlaying() || Boolean(currentResp.value) || Boolean(activeStudent.value)
}

function finishStudentSpeechUi(speechId) {
  if (speechId !== speechGeneration) return
  clearTimeout(clearRespTimer)
  clearRespTimer = null
  currentResp.value = null
  activeStudent.value = null
  clearStanding()
}

function isDeferredRoundBlocking() {
  return Boolean(pendingDeferredRound.value)
}

const questioningMergeHint = computed(() => {
  const pending = pendingDeferredRound.value
  if (!pending || pending.dialog_state !== 'questioning') return ''
  const count = Number(questioningBundle.value?.question_count || 0)
  if (count <= 1) return ''
  return `已合并 ${count} 个问题`
})

function getActiveDisciplineCount() {
  if (activeDisciplineEvent.value) return 1
  return 0
}

function pickDisciplineCandidateStudentId() {
  const blocked = new Set()
  if (activeStudent.value) blocked.add(activeStudent.value)
  for (const sid of Object.keys(poseByStudent.value)) {
    const p = poseByStudent.value[sid]
    if (!p) continue
    if (
      p.handRaised
      || p.standing
      || p.sleeping
      || p.whisperSide === 'left'
      || p.whisperSide === 'right'
    ) {
      blocked.add(sid)
    }
  }
  const candidates = students.value.map((s) => s.id).filter((id) => !blocked.has(id))
  if (!candidates.length) return null
  return candidates[Math.floor(Math.random() * candidates.length)]
}

function pickDisciplineAction(profile) {
  const w = profile?.event_weights || { sleep: 0.5, whisper: 0.5 }
  const sleepW = Number(w.sleep || 0)
  const whisperW = Number(w.whisper || 0)
  const sum = sleepW + whisperW
  if (sum <= 0) return Math.random() < 0.5 ? 'sleep' : 'whisper'
  const r = Math.random() * sum
  return r < sleepW ? 'sleep' : 'whisper'
}

function getDisciplineProfile() {
  return store.disciplineSimulationProfile || { enabled: false }
}

function startDisciplineScheduler() {
  stopDisciplineScheduler()
  lastDisciplineTickAtMs = 0
  lastDisciplineTriggeredAtMs = 0
  disciplineTickTimer = setInterval(() => {
    tickDisciplineRandomTrigger()
  }, 1000)
}

function stopDisciplineScheduler() {
  if (disciplineTickTimer) {
    clearInterval(disciplineTickTimer)
    disciplineTickTimer = null
  }
}

function triggerDisciplineEvent(studentId, action) {
  if (!studentId || (action !== 'sleep' && action !== 'whisper')) return
  applyDisciplinePose(studentId, action)
  const now = Date.now()
  activeDisciplineEvent.value = {
    student_id: studentId,
    action,
    started_at: nowIso(),
  }
  lastDisciplineTriggeredAtMs = now

  const disciplineAction = action === 'sleep' ? 'start_sleep' : 'start_whisper'
  enqueueTeacherSentence({
    role: 'teacher',
    content: lastTeacherSentence.value?.text || '（课堂纪律事件随机触发）',
    current_timestamp: nowIso(),
    called_student_id: studentId,
    discipline_action: disciplineAction,
    discipline_student_id: studentId,
  })
}

function tickDisciplineRandomTrigger() {
  if (!isRecording.value) return
  const profile = getDisciplineProfile()
  if (!profile?.enabled) return

  const now = Date.now()
  const startAfterMs = Number(profile.start_after_s || 0) * 1000
  if (elapsedSec.value * 1000 < startAfterMs) return

  const tickIntervalMs = Math.max(1000, Number(profile.tick_interval_s || 10) * 1000)
  if (now - lastDisciplineTickAtMs < tickIntervalMs) return
  lastDisciplineTickAtMs = now

  if (Number(profile.max_concurrent_events || 1) <= getActiveDisciplineCount()) return
  if (profile.block_while_student_speaking && isStudentSpeakingNow()) return
  if (profile.block_while_deferred_round_active && isDeferredRoundBlocking()) return

  const cooldownMs = Number(profile.event_cooldown_s || 0) * 1000
  if (cooldownMs > 0 && now - lastDisciplineTriggeredAtMs < cooldownMs) return

  const p = Number(profile.trigger_probability_per_tick || 0)
  if (!(Math.random() < p)) return

  const studentId = pickDisciplineCandidateStudentId()
  if (!studentId) return

  const action = pickDisciplineAction(profile)
  triggerDisciplineEvent(studentId, action)
}

function detectCalledStudent(text) {
  const raw = String(text || '')
  if (!raw) return null
  for (const s of students.value) {
    if (raw.includes(s.name)) {
      return { student_id: s.id, student_name: s.name }
    }
  }
  return null
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function isPointingSentence(text, calledStudent) {
  if (!calledStudent) return false
  const t = String(text || '')
  const n = escapeRegExp(calledStudent.student_name)
  const act = '(回答|答一下|答|说|说说|讲|讲讲|补充|补充一下|谈谈|解释|解释一下|说明|试试)'
  const p1 = new RegExp(`${n}[同学]?[，,、\\s]*(你)?(来|先)?${act}`)
  const p2 = new RegExp(`(请|麻烦|让)?[，,、\\s]*${n}[同学]?[，,、\\s]*(来|先)?${act}`)
  const p3 = new RegExp(`${n}[，,、\\s]*(来|先)?${act}`)
  const askQ1 = new RegExp(`${n}[同学]?[，,、\\s]*你?有(什么)?(问题|疑问)(吗)?[？?]?`)
  const askQ2 = new RegExp(`${n}[同学]?[，,、\\s]*你?想(问|说)(什么)?[？?]?`)
  return p1.test(t) || p2.test(t) || p3.test(t) || askQ1.test(t) || askQ2.test(t)
}

function buildCurrentPptText() {
  const slides = store.analysisResult?._raw?.slides
  if (!Array.isArray(slides)) {
    return hasPptMode.value ? `第 ${pptPage.value} 页内容待加载` : '当前未获取到PPT文本内容'
  }
  const one = slides.find((s) => Number(s.slide_no) === Number(pptPage.value))
  if (!one) return `第 ${pptPage.value} 页暂无文本内容`
  const parts = []
  if (one.title) parts.push(`标题：${one.title}`)
  if (Array.isArray(one.text_blocks) && one.text_blocks.length) {
    parts.push(`正文：${one.text_blocks.join('；')}`)
  }
  if (one.summary) parts.push(`摘要：${one.summary}`)
  return parts.join('。')
}

const currentPptTextDisplay = computed(() => buildCurrentPptText())

function buildCurrentPptPayload() {
  const slide =
    typeof store.currentPptSlide === 'function'
      ? store.currentPptSlide(pptPage.value)
      : null
  if (!slide) return null
  return [{
    slide_no: slide.slide_no,
    title: slide.title || `第 ${pptPage.value} 页`,
    text_blocks: Array.isArray(slide.text_blocks) ? slide.text_blocks : [],
    visual_elements: Array.isArray(slide.visual_elements) ? slide.visual_elements : [],
    summary: slide.summary || buildCurrentPptText(),
  }]
}

// ── Xfyun ASR setup ──
let asrClient = null
let asrReconnectTimer = null
let asrReconnectAttempt = 0
let asrReconnectInFlight = false
let asrStoppingManually = false

function clearAsrReconnectTimer() {
  if (asrReconnectTimer) {
    clearTimeout(asrReconnectTimer)
    asrReconnectTimer = null
  }
}

async function reconnectAsr(reason = '') {
  if (!isRecording.value || asrStoppingManually || asrReconnectInFlight) return
  asrReconnectInFlight = true
  try {
    if (!asrClient) {
      asrClient = buildXfyunClient()
      await asrClient.start()
    } else {
      await asrClient.resumeAfterFailure()
    }
    asrReconnectAttempt = 0
    micError.value = ''
    if (reason) console.info('[XFYUN ASR] reconnect success:', reason)
  } catch (err) {
    asrReconnectAttempt += 1
    scheduleAsrReconnect(err?.message || reason || '重连失败')
  } finally {
    asrReconnectInFlight = false
  }
}

function scheduleAsrReconnect(reason = '') {
  if (!isRecording.value || asrStoppingManually) return
  if (asrReconnectTimer) return
  const delayMs = Math.min(20000, 1000 * (2 ** Math.min(asrReconnectAttempt, 4)))
  micError.value = `⚠️ 语音连接波动，正在自动重连（${Math.round(delayMs / 1000)}s）…`
  asrReconnectTimer = setTimeout(async () => {
    asrReconnectTimer = null
    await reconnectAsr(reason)
  }, delayMs)
}

function stopTimer() {
  clearInterval(timerInterval)
  timerInterval = null
}

function nowIso() {
  return new Date().toISOString()
}

function nowClassElapsedSec() {
  return Math.max(0, Math.floor(Number(elapsedSec.value) || 0))
}

function currentSlideNo() {
  return hasPptMode.value ? pptPage.value : 0
}

function startNewSegment() {
  currentSegment = {
    segment_id: `seg-${Date.now()}-${segmentSeq++}`,
    start_ts: nowIso(),
    start_elapsed_sec: nowClassElapsedSec(),
    slide_no: currentSlideNo(),
    teacher_utterances: [],
    student_utterances: [],
  }
}

function shouldFlushNoPptSegment() {
  if (hasPptMode.value || !currentSegment) return false
  const startSec = Number(currentSegment.start_elapsed_sec || 0)
  return nowClassElapsedSec() - startSec >= NO_PPT_SEGMENT_WINDOW_SEC
}

function normalizeEvent(evt) {
  if (Array.isArray(evt)) {
    return normalizeEvent(evt[0] || null)
  }
  if (!evt || typeof evt !== 'object') return null
  return {
    student_type: evt.student_type || evt.agent_type || 'gangjing',
    reply_text: evt.reply_text || '（无回复）',
    emotion: evt.emotion || 'idle',
    is_triggered: Boolean(evt.is_triggered),
    is_proactive_speaking: Boolean(evt.is_proactive_speaking),
  }
}

function consumeCompletedSentences(chunk) {
  const out = []
  sentenceBuffer += chunk

  for (let i = 0; i < sentenceBuffer.length; i++) {
    if (/[。！？!?]/.test(sentenceBuffer[i])) {
      const sentence = sentenceBuffer.slice(0, i + 1).trim()
      if (sentence) out.push(sentence)
      sentenceBuffer = sentenceBuffer.slice(i + 1)
      i = -1
    }
  }
  return out
}

function normalizeAsrSentence(text) {
  return String(text || '')
    .trim()
    .replace(/\s+/g, '')
}

function shouldSkipDuplicateAsrSentence(sentence, tsIso) {
  const normalized = normalizeAsrSentence(sentence)
  if (!normalized) return true

  const nowMs = Number.isFinite(Date.parse(tsIso || ''))
    ? Date.parse(tsIso)
    : Date.now()

  while (recentAsrSentenceKeys.length) {
    const first = recentAsrSentenceKeys[0]
    if (nowMs - first.ts_ms <= ASR_SENTENCE_DUPLICATE_WINDOW_MS) break
    recentAsrSentenceKeys.shift()
  }

  const duplicated = recentAsrSentenceKeys.some((item) => item.key === normalized)
  if (duplicated) return true

  recentAsrSentenceKeys.push({ key: normalized, ts_ms: nowMs })
  return false
}

function flushResidualSentence() {
  const rest = sentenceBuffer.trim()
  sentenceBuffer = ''
  if (!rest) return
  const ts = nowIso()
  const classElapsedSec = nowClassElapsedSec()
  if (shouldSkipDuplicateAsrSentence(rest, ts)) return
  handleTeacherSentence(rest, ts, classElapsedSec)
}

function mergeFinalWithInterim(finalText, interim) {
  const f = String(finalText || '').trim()
  const i = String(interim || '').trim()
  if (!i) return f
  if (!f) return i
  if (f.includes(i)) return f
  if (i.includes(f)) return i
  return `${i}${f}`
}

/** 讯飞 interim 每次返回当前整句猜测，直接覆盖而非拼接 */
function mergeInterimText(_prev, incoming) {
  return String(incoming || '')
}

/** 写入正式转写时去掉与已有尾部重叠的部分，避免 interim 兜底 + final 重复上屏 */
function appendTranscriptChunk(chunk) {
  const c = String(chunk || '').trim()
  if (!c) return ''

  const prev = transcript.value
  if (!prev) {
    transcript.value = c
    return c
  }
  if (prev.endsWith(c)) return ''

  let overlap = 0
  const maxOverlap = Math.min(prev.length, c.length)
  for (let i = maxOverlap; i > 0; i -= 1) {
    if (prev.endsWith(c.slice(0, i))) {
      overlap = i
      break
    }
  }
  const delta = c.slice(overlap)
  if (!delta) return ''
  transcript.value += delta
  return delta
}

function commitInterimAsFinal() {
  const pending = String(interimText.value || '').trim()
  if (!pending) return
  interimText.value = ''
  const appended = appendTranscriptChunk(pending)
  if (!appended) return
  const completed = consumeCompletedSentences(appended)
  completed.forEach((sentence) => {
    const ts = nowIso()
    const classElapsedSec = nowClassElapsedSec()
    if (shouldSkipDuplicateAsrSentence(sentence, ts)) return
    handleTeacherSentence(sentence, ts, classElapsedSec)
  })
}

function isNoiseOnlyAsrText(text) {
  const t = String(text || '').trim()
  if (!t) return true
  return /^[嗯呃啊哦]+[。，、！？…]*$/.test(t)
}

function appendTranscript(text, meta = {}) {
  if (!text?.trim()) return
  if (isNoiseOnlyAsrText(text)) return
  if (Date.now() < asrMuteUntilMs) return
  micError.value = ''
  const isFinal = Boolean(meta?.isFinal)
  if (!isFinal) {
    // interim: 快速上屏，做增量累积，避免只显示末尾几个字。
    interimText.value = mergeInterimText(interimText.value, text)
    clearTimeout(interimCommitTimer)
    // 兜底：若迟迟等不到 final，避免长期只显示灰字不落库。
    interimCommitTimer = setTimeout(() => {
      commitInterimAsFinal()
    }, 1200)
    nextTick(() => {
      if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
    })
    return
  }
  clearTimeout(interimCommitTimer)

  const merged = mergeFinalWithInterim(text, interimText.value)
  interimText.value = ''
  const committed = appendTranscriptChunk(merged)
  if (!committed) return

  nextTick(() => {
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  })

  const completed = consumeCompletedSentences(committed)
  completed.forEach((sentence) => {
    const ts = nowIso()
    const classElapsedSec = nowClassElapsedSec()
    if (shouldSkipDuplicateAsrSentence(sentence, ts)) return
    handleTeacherSentence(sentence, ts, classElapsedSec)
  })
}

function showPipelineError(message) {
  pipelineError.value = message
  clearTimeout(clearPipelineErrorTimer)
  clearPipelineErrorTimer = setTimeout(() => {
    pipelineError.value = ''
  }, 7000)
}

function buildXfyunClient() {
  return new XfyunASRClient({
    onText: appendTranscript,
    onError: (message) => {
      console.warn('[XFYUN ASR] fatal:', message)
      if (!isRecording.value || asrStoppingManually) return
      scheduleAsrReconnect(message)
    },
    // 句末轮转 / 10165 静默续听在 XfyunASRClient 内部处理，不在 onClose 里整段重连
    onClose: () => {},
  })
}

function enqueueTeacherSentence(task) {
  if (shouldSkipDuplicateTeacherTask(task)) return
  supervisorQueue.push(task)
  processSupervisorQueue()
}

function normalizeTeacherContent(text) {
  return String(text || '').trim().replace(/\s+/g, ' ')
}

function shouldSkipDuplicateTeacherTask(task) {
  if (!task || task.role !== 'teacher') return false
  const content = normalizeTeacherContent(task.content)
  if (!content) return true

  const nowMs = Number.isFinite(Date.parse(task.current_timestamp || ''))
    ? Date.parse(task.current_timestamp)
    : Date.now()

  while (recentTeacherUploadKeys.length) {
    const first = recentTeacherUploadKeys[0]
    if (nowMs - first.ts_ms <= TEACHER_DUPLICATE_WINDOW_MS) break
    recentTeacherUploadKeys.shift()
  }

  const dedupKey = `${content}__${task.called_student_id || ''}`
  const duplicated = recentTeacherUploadKeys.some((item) => item.key === dedupKey)
  if (duplicated) return true

  recentTeacherUploadKeys.push({ key: dedupKey, ts_ms: nowMs })
  return false
}

function shouldSkipDuplicatePointingReply(text, calledStudentId, tsIso) {
  const content = normalizeTeacherContent(text)
  const dedupKey = `${content}__${calledStudentId || ''}`
  const nowMs = Number.isFinite(Date.parse(tsIso || ''))
    ? Date.parse(tsIso)
    : Date.now()

  while (recentPointingReplyKeys.length) {
    const first = recentPointingReplyKeys[0]
    if (nowMs - first.ts_ms <= POINTING_REPLY_DUPLICATE_WINDOW_MS) break
    recentPointingReplyKeys.shift()
  }

  const duplicated = recentPointingReplyKeys.some((item) => item.key === dedupKey)
  if (duplicated) return true
  recentPointingReplyKeys.push({ key: dedupKey, ts_ms: nowMs })
  return false
}

const MOCK_QUESTIONING_RESPONSE = {
  dialog_state: 'questioning',
  should_trigger_student: true,
  trigger_reason: 'teacher_question',
  target_student_type: 'all',
  student_event: [
    {
      student_type: 'xueyou',
      emotion: 'curious',
      reply_text: '老师，是不是只有直角三角形才能用 a²+b²=c²？',
      is_triggered: false,
      is_proactive_speaking: true,
    },
    {
      student_type: 'xueyou',
      emotion: 'curious',
      reply_text: '老师我试着答：这个结论可能只在特定条件下成立。',
      is_triggered: false,
      is_proactive_speaking: false,
    },
    {
      student_type: 'gangjing',
      emotion: 'curious',
      reply_text: '老师我来答：任意三角形不能直接套勾股，除非先证成直角。',
      is_triggered: false,
      is_proactive_speaking: true,
    },
    {
      student_type: 'gangjing',
      emotion: 'curious',
      reply_text: '老师我觉得这里有漏洞：没直角条件就不能直接下结论。',
      is_triggered: false,
      is_proactive_speaking: false,
    },
    {
      student_type: 'xuekun',
      emotion: 'hesitant',
      reply_text: '老师我来答：是不是要先确认这是直角三角形再用公式？',
      is_triggered: false,
      is_proactive_speaking: true,
    },
    {
      student_type: 'xuekun',
      emotion: 'hesitant',
      reply_text: '老师我试着答：我觉得要先看是不是直角，但细节可能不全。',
      is_triggered: false,
      is_proactive_speaking: false,
    },
  ],
}

function appendChat(role, content, current_timestamp, called_student_id = null) {
  chatHistory.value.push({
    role,
    content,
    current_timestamp,
    called_student_id,
  })
}

function looksQuestioning(text) {
  const t = String(text || '')
  return /[?？]/.test(t) || /(谁来|谁能|请回答|你怎么看|解释一下)/.test(t)
}

async function getStudentStateFromBackend(studentId) {
  try {
    return await fetchStudentState(studentId)
  } catch {
    // 后端未就绪时兜底，仅用于本地联调
    const fallback = {
      student_xm: { student_id: 'student_xm', student_type: 'xueyou', is_hand_raised: false },
      student_xw: { student_id: 'student_xw', student_type: 'gangjing', is_hand_raised: true },
      student_xw2: { student_id: 'student_xw2', student_type: 'xuekun', is_hand_raised: false },
      student_xl: { student_id: 'student_xl', student_type: 'xuekun', is_hand_raised: true },
    }
    return fallback[studentId] || { student_id: studentId, student_type: 'xuekun', is_hand_raised: false }
  }
}

function pickPresetForCalledStudent(events, studentState) {
  if (!Array.isArray(events) || !events.length || !studentState) return null
  const t = studentState.student_type
  const raised = Boolean(studentState.is_hand_raised)
  const exact = events.find((e) => e.student_type === t && Boolean(e.is_proactive_speaking) === raised)
  if (exact) return exact
  return events.find((e) => e.student_type === t) || events[0] || null
}

async function processSupervisorQueue() {
  if (supervisorBusy || supervisorQueue.length === 0) return
  supervisorBusy = true
  try {
    while (supervisorQueue.length) {
      const task = supervisorQueue.shift()
      const payload = {
        session_id: currentSessionId.value,
        current_timestamp: task.current_timestamp,
        class_elapsed_sec: task.class_elapsed_sec,
        role: task.role,
        content: task.content,
        called_student_id: task.called_student_id || null,
        slide_no: currentSlideNo(),
      }
      if (task.discipline_action) payload.discipline_action = task.discipline_action
      if (task.discipline_student_id) payload.discipline_student_id = task.discipline_student_id

      let result = null
      try {
        result = await postInclassUtterance(payload)
      } catch (e) {
        result = null
        const msg = String(e?.message || '')
        if (msg.includes('502') || msg.includes('504') || msg.includes('超时')) {
          showPipelineError('本句 AI 超时/失败，未触发学生响应；可继续讲或重复提问。')
        } else {
          showPipelineError('本句后端处理失败，未触发学生响应；请稍后重试。')
        }
      }

      // 联调兜底：默认关闭，避免真实课堂测试混入 mock 回答
      if (
        ENABLE_MOCK_QUESTIONING_FALLBACK
        && !result
        && task.role === 'teacher'
        && looksQuestioning(task.content)
      ) {
        result = MOCK_QUESTIONING_RESPONSE
      }

      if (result) {
        await handleSupervisorResult(result, task)
      }
    }
  } catch (e) {
    console.warn('[Backend inclass pipeline] 暂不可用', e.message)
  } finally {
    supervisorBusy = false
    if (supervisorQueue.length) processSupervisorQueue()
  }
}

async function handleSupervisorResult(result, task = {}) {
  if (!result) return
  updateDigestMap(result.student_states_digest)

  const dialogState = String(result.dialog_state || 'normal')
  const playMode = String(result.play_mode || 'immediate')
  const raisedIds = Array.isArray(result.raised_hand_student_ids) ? result.raised_hand_student_ids : []
  const presetId = result.preset_for_student_id || null
  const roundId = result.interaction_round_id || nowIso()
  const taskTs = Number.isFinite(Date.parse(task?.current_timestamp || ''))
    ? Date.parse(task.current_timestamp)
    : 0

  // 新句被判 normal 说明前一轮延迟触发已失效，避免旧 misstatement/questioning 残留
  if (dialogState === 'normal') {
    clearDeferredRound(true)
    return
  }

  // 防止"已点名作答后，旧 teacher 句子迟到返回 questioning"又把举手刷回去
  if (
    isDeferredDialogState(dialogState)
    && taskTs > 0
    && lastStudentSpeechAtMs.value > 0
    && taskTs < lastStudentSpeechAtMs.value
  ) {
    return
  }

  // 统一处理延迟触发回合：同一时刻只保留一个，后来的覆盖之前的
  if (isDeferredDialogState(dialogState) && playMode === 'on_call_name') {
    if (dialogState === 'questioning') {
      const activePending = pendingDeferredRound.value
      if (
        activePending
        && activePending.dialog_state === 'questioning'
        && activePending.bundle_locked
      ) {
        return
      }
      // Supervisor 不再预生成 6 条候选，只返回元数据；前端只保留举手状态
      latestQuestioningEvents.value = []
      candidatePool.value = {}
      candidateEvents.value = []
      appendQuestioningBundleFromTask(task, roundId)
      replaceDeferredRound({
        roundId,
        dialog_state: dialogState,
        created_at_ms: taskTs > 0 ? taskTs : Date.now(),
        raised_hand_student_ids: raisedIds,
        preset_for_student_id: null,
        events: [],
        question_bundle: questioningBundle.value,
      })
      return
    }

    const one = normalizeEvent(result.student_event)
    if (!one) return
    candidateEvents.value = []
    replaceDeferredRound({
      roundId,
      dialog_state: dialogState,
      raised_hand_student_ids: raisedIds,
      preset_for_student_id: presetId,
      event: one,
    })
    return
  }

  // immediate 场景：relay_answer / discipline_* 等，直接站立 + 语音播放
  const one = normalizeEvent(result.student_event)
  if (!one) return
  if (dialogState === 'discipline_whisper' || dialogState === 'discipline_sleep') {
    activeDisciplineEvent.value = null
    clearAllDisciplinePoses()
  }
  clearDeferredRound(true)
  const targetId = presetId || task.called_student_id || resolveStudentIdForEvent(one)
  await playStudentEvent({
    ...one,
    student_id: targetId || one.student_id,
  })
}

function findStudentById(id) {
  return students.value.find((s) => s.id === id) || null
}

async function handleTeacherSentence(text, ts, classElapsedSec = nowClassElapsedSec()) {
  if (!text) return
  if (!currentSegment) startNewSegment()

  const calledStudent = detectCalledStudent(text)
  const calledId = calledStudent?.student_id || null
  const pointing = isPointingSentence(text, calledStudent)

  currentSegment.teacher_utterances.push({ speaker: 'teacher', ts, text })
  appendChat('teacher', text, ts, calledId)
  lastTeacherSentence.value = { text, ts, called_student_id: calledId }

  // 点名句 + 延迟触发回合：前端直接消费，不交 supervisor
  const pending = pendingDeferredRound.value
  if (pointing && calledId && pending) {
    if (shouldSkipDuplicatePointingReply(text, calledId, ts)) {
      return
    }

    if (pending.dialog_state === 'questioning') {
      let state = getDigestState(calledId)
      if (!state) state = await getStudentStateFromBackend(calledId)

      // 实时调用后端生成被点名学生的单条回复
      let reply
      try {
        const bundle = pending.question_bundle || questioningBundle.value
        reply = await postStudentReply({
          session_id: currentSessionId.value,
          student_id: calledId,
          current_timestamp: ts,
          class_elapsed_sec: classElapsedSec,
          slide_no: currentSlideNo(),
          question_bundle_text: bundle?.merged_text || '',
          question_count: Number(bundle?.question_count || 0),
          question_items: Array.isArray(bundle?.items) ? bundle.items : [],
        })
      } catch (e) {
        showPipelineError(`获取 ${calledStudent?.student_name || '学生'} 回复失败，请继续授课`)
        clearDeferredRound(true)
        return
      }

      const studentMeta = findStudentById(calledId)
      await playStudentEvent({
        student_id: calledId,
        student_name: studentMeta?.name || calledStudent?.student_name || '学生',
        student_type: reply.student_type,
        reply_text: reply.reply_text,
        emotion: reply.emotion,
        is_proactive_speaking: reply.is_proactive_speaking,
        is_triggered: true,
      })
      clearDeferredRound(true)
      if (shouldFlushNoPptSegment()) {
        flushCurrentSegment('no_ppt_30s_sentence_complete')
      }
      return
    }

    if (
      (pending.dialog_state === 'ambiguous' || pending.dialog_state === 'misstatement') &&
      pending.preset_for_student_id &&
      pending.preset_for_student_id === calledId &&
      pending.event
    ) {
      const studentMeta = findStudentById(calledId)
      await playStudentEvent({
        ...pending.event,
        student_id: calledId,
        student_name: studentMeta?.name || calledStudent?.student_name || '学生',
        academic_type: pending.event.student_type,
      })
      clearDeferredRound(true)
      if (shouldFlushNoPptSegment()) {
        flushCurrentSegment('no_ppt_30s_sentence_complete')
      }
      return
    }

    // 延迟回合未命中时不调用 supervisor，保留当前待触发缓存
    return
  }
  // 其他句子：正常交后端（后端自行决定是否调用 supervisor）
  enqueueTeacherSentence({
    role: 'teacher',
    content: text,
    current_timestamp: ts,
    class_elapsed_sec: classElapsedSec,
    called_student_id: calledId,
  })

  if (shouldFlushNoPptSegment()) {
    flushCurrentSegment('no_ppt_30s_sentence_complete')
  }
}

function triggerCandidate(evt) {
  const chosen = normalizeEvent(evt)
  if (!chosen) return
  if (evt?.student_id) chosen.student_id = evt.student_id
  if (evt?.student_name) chosen.student_name = evt.student_name
  if (evt?.academic_type) chosen.academic_type = evt.academic_type
  chosen.is_triggered = true
  playStudentEvent(chosen)
  candidateEvents.value = []
}

async function playStudentEvent(eventObj) {
  const resp = normalizeEvent(eventObj)
  if (!resp) return
  if (eventObj?.student_id) resp.student_id = eventObj.student_id
  if (eventObj?.student_name) resp.student_name = eventObj.student_name
  if (eventObj?.academic_type) resp.academic_type = eventObj.academic_type

  const profile = resp.student_id ? findStudentById(resp.student_id) : null
  if (!resp.student_name && profile) resp.student_name = profile.name
  // 任意学生开始发言时，前端立即清空所有举手动画，避免残留
  clearAllHands()
  if (resp.student_id) setStandingStudent(resp.student_id)

  const ts = nowIso()
  lastStudentSpeechAtMs.value = Date.parse(ts)
  if (!currentSegment) startNewSegment()
  currentSegment.student_utterances.push({
    speaker: resp.student_name || resp.student_type,
    ts,
    text: resp.reply_text,
  })
  appendChat(resp.student_name || resp.student_type, resp.reply_text, ts, null)

  currentResp.value = resp
  activeStudent.value = resolveStudentIdForEvent(resp)
  sessionLog.value.push(resp)
  enqueueTeacherSentence({
    role: 'student',
    content: resp.reply_text,
    current_timestamp: ts,
    class_elapsed_sec: nowClassElapsedSec(),
    called_student_id: null,
  })

  const speechId = ++speechGeneration
  try {
    await speakStudent(resp.reply_text, resp.student_id, resp.student_type)
    if (speechId === speechGeneration) {
      asrMuteUntilMs = Math.max(asrMuteUntilMs, Date.now() + 800)
    }
  } catch (e) {
    if (e?.message !== 'speech-cancelled' && e?.message !== 'MiniMax playback cancelled') {
      console.warn('[TTS] 播放失败，仍结束站立姿态：', e?.message || e)
    }
  } finally {
    finishStudentSpeechUi(speechId)
  }
}

async function flushCurrentSegment(reason = 'manual') {
  if (!currentSegment) return
  const hasContent =
    currentSegment.teacher_utterances.length || currentSegment.student_utterances.length
  if (!hasContent) {
    startNewSegment()
    return
  }

  // 先切换到新段，避免网络请求期间写入旧段造成边界混乱
  const segmentToFlush = currentSegment
  startNewSegment()

  const payload = {
    session_id: currentSessionId.value,
    segment_id: segmentToFlush.segment_id,
    start_ts: segmentToFlush.start_ts,
    end_ts: nowIso(),
    start_elapsed_sec: segmentToFlush.start_elapsed_sec,
    end_elapsed_sec: nowClassElapsedSec(),
    slide_no: segmentToFlush.slide_no,
    teacher_utterances: segmentToFlush.teacher_utterances,
    student_utterances: segmentToFlush.student_utterances,
    current_ppt: buildCurrentPptPayload(),
  }
  payload.ppt_text = buildCurrentPptText()

  try {
    const evalRes = await postInclassSegment(payload)
    segmentEvalResults.value.push({
      ...evalRes,
      flush_reason: reason,
    })
  } catch (e) {
    console.warn('[Segment Eval v2] 失败，保留本地段数据：', e.message)
    segmentEvalResults.value.push({
      ...payload,
      eval_error: e.message,
      flush_reason: reason,
    })
  }
}

// ── TTS：优先后端 MiniMax T2A，失败则浏览器原生；播完才 resolve ──
function cancelBrowserSpeech() {
  if (browserSpeechReject) {
    const reject = browserSpeechReject
    browserSpeechReject = null
    reject(new Error('speech-cancelled'))
  }
  window.speechSynthesis?.cancel()
}

function cancelAllSpeech() {
  stopMinimaxPlayback()
  cancelBrowserSpeech()
}

function speakWithBrowser(text, agentType) {
  const trimmed = String(text || '').trim()
  if (!trimmed) return Promise.resolve()
  if (!window.speechSynthesis) return Promise.resolve()

  cancelBrowserSpeech()

  return new Promise((resolve, reject) => {
    browserSpeechReject = reject
    const u = new SpeechSynthesisUtterance(trimmed)
    u.lang = 'zh-CN'

    switch (agentType) {
      case 'gangjing': u.pitch = 1.25; u.rate = 1.1;  break
      case 'xuekun':   u.pitch = 0.85; u.rate = 0.88; break
      case 'sleepy':   u.pitch = 0.70; u.rate = 0.80; break
      case 'whisper':  u.pitch = 1.00; u.rate = 0.95; u.volume = 0.65; break
      default:         u.pitch = 1.00; u.rate = 0.95
    }

    const done = (err) => {
      if (browserSpeechReject !== reject) return
      browserSpeechReject = null
      if (err) reject(err)
      else resolve()
    }

    u.onend = () => done()
    u.onerror = () => done(new Error('browser-tts-error'))
    window.speechSynthesis.speak(u)
  })
}

async function speakStudent(text, studentId, agentType) {
  cancelAllSpeech()
  const usedMinimax = await minimaxSpeak(text, {
    studentId: studentId || null,
  })
  if (usedMinimax) return
  await speakWithBrowser(text, agentType)
}

// ── Controls ──
async function toggleRecording() {
  if (!asrSupported.value) return
  micError.value = ''

  if (isRecording.value) {
    // — STOP —
    asrStoppingManually = true
    isRecording.value = false
    stopTimer()
    stopDisciplineScheduler()
    clearAsrReconnectTimer()
    pipelineError.value = ''
    clearTimeout(clearPipelineErrorTimer)
    asrReconnectAttempt = 0
    asrClient?.stop()
    recentTeacherUploadKeys.length = 0
    recentAsrSentenceKeys.length = 0
    clearTimeout(interimCommitTimer)
    interimCommitTimer = null
    flushResidualSentence()
    commitInterimAsFinal()
    await flushCurrentSegment('manual_stop')
    cancelAllSpeech()
    asrStoppingManually = false
    hasShownDurationWarn.value = false
    return
  }

  try {
    asrStoppingManually = false
    clearAsrReconnectTimer()
    asrReconnectAttempt = 0
    asrClient = buildXfyunClient()
    await asrClient.start()
    isRecording.value = true
    chatHistory.value = []
    candidateEvents.value = []
    candidatePool.value = {}
    latestQuestioningEvents.value = []
    recentTeacherUploadKeys.length = 0
    recentAsrSentenceKeys.length = 0
    pendingDeferredRound.value = null
    latestStateDigestMap.value = {}
    activeDisciplineEvent.value = null
    initPoseState()
    if (!currentSegment) startNewSegment()
    stopTimer()  // clear any stale interval before starting a new one
    hasShownDurationWarn.value = false
    timerInterval = setInterval(() => elapsedSec.value++, 1000)
    startDisciplineScheduler()
  } catch (err) {
    const message = err?.message || '未知错误'
    if (message.includes('未登录') || message.includes('过期')) {
      micError.value = '❌ 登录已过期，请重新登录后再试。'
    } else if (message.includes('配置缺失') || message.includes('XFYUN')) {
      micError.value = '❌ 讯飞 ASR 后端配置缺失：请联系管理员在后端 .env 设置 XFYUN_APP_ID / XFYUN_API_KEY / XFYUN_API_SECRET。'
    } else if (message.includes('Permission denied') || message.includes('denied')) {
      micError.value = '❌ 麦克风权限被拒绝，请点击地址栏左侧锁图标允许麦克风访问后重试。'
    } else {
      micError.value = `❌ 无法启动讯飞语音识别：${message}`
    }
  }
}

async function endClass() {
  asrStoppingManually = true
  clearAsrReconnectTimer()
  pipelineError.value = ''
  clearTimeout(clearPipelineErrorTimer)
  asrClient?.stop()
  recentTeacherUploadKeys.length = 0
  recentAsrSentenceKeys.length = 0
  clearTimeout(interimCommitTimer)
  interimCommitTimer = null
  stopTimer()
  stopDisciplineScheduler()
  flushResidualSentence()
  commitInterimAsFinal()
  await flushCurrentSegment('end_class')
  speechGeneration += 1
  cancelAllSpeech()
  clearDeferredRound(true)
  clearStanding()
  activeDisciplineEvent.value = null
  clearAllDisciplinePoses()
  // 停止视觉采样（会上传最后一段）
  if (visualEnabled.value) {
    await _stopVisualSampling().catch(() => {})
  }
  router.push(`/report/${currentSessionId.value}`)
}

onUnmounted(() => {
  _stopCamera()
  clearTimeout(pptPaintDebounceTimer)
  pptPaintDebounceTimer = null
  pdfResizeObserver?.disconnect()
  pdfResizeObserver = null
  invalidatePptPdfCache()
  pptPreviewRequestToken += 1
  stopTimer()
  asrStoppingManually = true
  clearAsrReconnectTimer()
  pipelineError.value = ''
  clearTimeout(clearPipelineErrorTimer)
  asrClient?.stop()
  recentTeacherUploadKeys.length = 0
  recentAsrSentenceKeys.length = 0
  clearTimeout(interimCommitTimer)
  interimCommitTimer = null
  stopDisciplineScheduler()
  clearTimeout(clearRespTimer)
  clearTimeout(clearPipelineErrorTimer)
  speechGeneration += 1
  cancelAllSpeech()
  clearDeferredRound(true)
  clearStanding()
  activeDisciplineEvent.value = null
  clearAllDisciplinePoses()
  if (String(pptPreviewUrl.value || '').startsWith('blob:')) {
    URL.revokeObjectURL(pptPreviewUrl.value)
    pptPreviewUrl.value = ''
  }
})

startNewSegment()
initPoseState()
void recoverSessionContextIfNeeded()

// ══════════════════════════════════════════════════════
// ── 视觉分析模块（教姿教态）──
// ══════════════════════════════════════════════════════

const VISUAL_CONSENT_KEY = 'teachsim_visual_consent_v2'
const VISUAL_WINDOW_SEC = 15
const VISUAL_MOTION_THRESHOLD = 8        // canvas 帧差运动检测阈值

// 同意弹窗
const showVisualConsentModal = ref(false)
const visualCameraSupported = ref(false)
// 摄像头状态
const visualEnabled = ref(false)
const visualStream = ref(null)
const visualVideoRef = ref(null)
const visualCanvasRef = ref(null)

// 内部状态
let _visualWindowIndex = 0
let _visualWindowTimer = null
let _visualMediaRecorder = null
let _visualRecordedChunks = []
let _visualLastFrameData = null
let _visualMotionFrameCount = 0
let _visualActiveWindowStartSec = 0

function _hasVisualConsent() {
  try { return localStorage.getItem(VISUAL_CONSENT_KEY) === '1' } catch { return false }
}
function _saveVisualConsent() {
  try { localStorage.setItem(VISUAL_CONSENT_KEY, '1') } catch {}
}

/** 初始化摄像头（仅摄像头流，无需显示给用户） */
async function _initCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
      audio: false,
    })
    visualStream.value = stream
    if (visualVideoRef.value) {
      visualVideoRef.value.srcObject = stream
      visualVideoRef.value.play().catch(() => {})
    }
    return true
  } catch (e) {
    console.warn('[Visual] 摄像头权限被拒绝或不可用', e?.message)
    return false
  }
}

/** 停止摄像头流和定时器（结束课堂时调用） */
function _stopCamera() {
  if (_visualWindowTimer) { clearInterval(_visualWindowTimer); _visualWindowTimer = null }
  if (_visualMediaRecorder && _visualMediaRecorder.state !== 'inactive') {
    try { _visualMediaRecorder.stop() } catch {}
  }
  _visualMediaRecorder = null
  _visualRecordedChunks = []
  if (visualStream.value) {
    visualStream.value.getTracks().forEach(t => t.stop())
    visualStream.value = null
  }
  visualEnabled.value = false
}

/** 暂停采样：上传当前窗口，但保持摄像头流（暂停授课时用） */
async function _pauseVisualSampling() {
  if (_visualWindowTimer) { clearInterval(_visualWindowTimer); _visualWindowTimer = null }
  const clipBlob = await _stopRecording()
  const f = _captureFrame()
  const framesB64 = f ? [f] : []
  if (framesB64.length || clipBlob) {
    await _processVisualWindow(framesB64, clipBlob)
  }
}

/**
 * 简单运动检测：对比当前帧与上一帧像素均方差。
 * 无 MediaPipe 依赖，依赖 canvas 像素差分。
 * 返回 true 表示有足够运动（说明有人在画面里动作）。
 */
function _motionPrecheck() {
  const video = visualVideoRef.value
  const canvas = visualCanvasRef.value
  if (!video || !canvas || !video.videoWidth) return false
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  canvas.width = 80
  canvas.height = 60
  ctx.drawImage(video, 0, 0, 80, 60)
  const cur = ctx.getImageData(0, 0, 80, 60).data
  if (!_visualLastFrameData) {
    _visualLastFrameData = cur.slice()
    return true
  }
  let diff = 0
  for (let i = 0; i < cur.length; i += 4) {
    diff += Math.abs(cur[i] - _visualLastFrameData[i])
  }
  const avgDiff = diff / (80 * 60)
  _visualLastFrameData = cur.slice()
  return avgDiff >= VISUAL_MOTION_THRESHOLD
}

/** 从 video 抓取一帧 base64 JPEG */
function _captureFrame() {
  const video = visualVideoRef.value
  const canvas = visualCanvasRef.value
  if (!video || !canvas || !video.videoWidth) return null
  const ctx = canvas.getContext('2d')
  canvas.width = 640
  canvas.height = 480
  ctx.drawImage(video, 0, 0, 640, 480)
  const dataUrl = canvas.toDataURL('image/jpeg', 0.7)
  return dataUrl.replace(/^data:image\/jpeg;base64,/, '')
}

/** 采集 3 帧（窗口开始 / 中间 / 结束前各一帧），每隔 VISUAL_WINDOW_SEC/3 秒取一次 */
async function _collectWindowFrames() {
  const frames = []
  const interval = (VISUAL_WINDOW_SEC * 1000) / 3
  for (let i = 0; i < 3; i++) {
    const f = _captureFrame()
    if (f) frames.push(f)
    if (i < 2) await new Promise(r => setTimeout(r, interval))
  }
  return frames
}

/** 启动 MediaRecorder 录制 */
function _startRecording() {
  const stream = visualStream.value
  if (!stream) return
  _visualRecordedChunks = []
  try {
    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
      ? 'video/webm;codecs=vp9'
      : 'video/webm'
    _visualMediaRecorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: 400_000 })
    _visualMediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) _visualRecordedChunks.push(e.data)
    }
    _visualMediaRecorder.start(500)
  } catch (e) {
    console.warn('[Visual] MediaRecorder 启动失败', e?.message)
    _visualMediaRecorder = null
  }
}

/** 停止录制并返回 Blob */
function _stopRecording() {
  return new Promise(resolve => {
    if (!_visualMediaRecorder || _visualMediaRecorder.state === 'inactive') {
      resolve(null); return
    }
    _visualMediaRecorder.onstop = () => {
      const blob = _visualRecordedChunks.length
        ? new Blob(_visualRecordedChunks, { type: 'video/webm' })
        : null
      _visualRecordedChunks = []
      resolve(blob)
    }
    try { _visualMediaRecorder.stop() } catch { resolve(null) }
  })
}

/** 处理一个 15s 窗口的上传 */
async function _processVisualWindow(framesB64, clipBlob) {
  const windowIdx = _visualWindowIndex++
  const observationId = `${currentSessionId.value}_w${windowIdx}`
  const windowStartSec = _visualActiveWindowStartSec

  const precheckPassed = framesB64.length > 0

  try {
    await postVisualObservation({
      sessionId: currentSessionId.value,
      observationId,
      segmentId: currentSegment?.id || null,
      windowStartSec,
      windowEndSec: windowStartSec + VISUAL_WINDOW_SEC,
      slideNo: pptPage.value || null,
      precheckPassed,
      framesB64,
      clip: clipBlob,
      chatHistory: chatHistory.value.slice(-20),
    })
  } catch (e) {
    console.warn('[Visual] 上传失败，跳过本窗口', e?.message)
  }
}

/** 启动 15s 轮转采样 */
async function _startVisualSampling() {
  if (!visualEnabled.value || _visualWindowTimer) return
  if (!visualStream.value) {
    const ok = await _initCamera()
    if (!ok) return
  }
  _visualActiveWindowStartSec = elapsedSec.value
  _startRecording()

  // 每 VISUAL_WINDOW_SEC 触发一次采集
  _visualWindowTimer = setInterval(async () => {
    if (!isRecording.value) return
    const motionOk = _motionPrecheck()
    if (!motionOk) { _visualMotionFrameCount++ }

    let framesB64 = []
    if (motionOk) {
      const f1 = _captureFrame()
      await new Promise(r => setTimeout(r, 1000))
      const f2 = _captureFrame()
      await new Promise(r => setTimeout(r, 1000))
      const f3 = _captureFrame()
      framesB64 = [f1, f2, f3].filter(Boolean)
    } else {
      const f = _captureFrame()
      if (f) framesB64 = [f]
    }

    // 停止当前录制段
    const clipBlob = await _stopRecording()

    // 上传（后台异步，不阻塞采样循环）
    _visualActiveWindowStartSec = elapsedSec.value
    _processVisualWindow(framesB64, clipBlob).catch(() => {})

    // 开始下一段录制
    if (isRecording.value && visualEnabled.value) {
      _startRecording()
    }
  }, VISUAL_WINDOW_SEC * 1000)
}

/** 停止视觉采样并上传最后一个窗口（结束课堂） */
async function _stopVisualSampling() {
  await _pauseVisualSampling()
  _stopCamera()
}

/** 首次进入教室时检查同意状态 */
function initVisualConsent() {
  visualCameraSupported.value = Boolean(
    window.isSecureContext &&
      navigator.mediaDevices?.getUserMedia,
  )

  if (_hasVisualConsent()) {
    if (!visualCameraSupported.value) {
      console.warn('[Visual] 已同意教姿分析，但当前环境不支持摄像头')
      return
    }
    void nextTick().then(async () => {
      const ok = await _initCamera()
      if (ok) visualEnabled.value = true
    })
    return
  }

  showVisualConsentModal.value = true
  console.info('[Visual] 显示教姿分析同意弹窗')
}

async function onVisualConsentAgree() {
  _saveVisualConsent()
  showVisualConsentModal.value = false
  const ok = await _initCamera()
  if (ok) visualEnabled.value = true
}

function onVisualConsentDecline() {
  showVisualConsentModal.value = false
}

// 当开始授课时同步开启视觉采样
watch(isRecording, async (val) => {
  if (val && visualEnabled.value) {
    await _startVisualSampling()
  } else if (!val && visualEnabled.value) {
    await _pauseVisualSampling()
  }
})

onMounted(() => {
  void nextTick().then(() => initVisualConsent())
})
</script>

<style scoped>
/* ── Root ── */
.classroom-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #050B18;
  color: #E2E8F0;
  font-family: system-ui, -apple-system, sans-serif;
  overflow: hidden;
}

/* ── Header ── */
.hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 52px;
  border-bottom: 1px solid rgba(34,211,238,0.12);
  background: rgba(5,11,24,0.95);
  flex-shrink: 0;
}
.hdr-center { display: flex; align-items: center; gap: 14px; }
.hdr-btn {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 500; color: #94A3B8;
  background: none; border: 1px solid rgba(148,163,184,0.2); border-radius: 8px;
  padding: 6px 14px; cursor: pointer; text-decoration: none;
  transition: all 0.2s;
}
.hdr-btn:hover { color: #22D3EE; border-color: rgba(34,211,238,0.4); }
.hdr-end { color: #F87171; }
.hdr-end:hover { color: #FCA5A5; border-color: rgba(248,113,113,0.4); }

.mode-pill {
  font-size: 12px; font-weight: 600; padding: 3px 12px; border-radius: 20px;
  letter-spacing: 0.5px;
}
.mode-full    { background: rgba(168,85,247,0.2); color: #C084FC; border: 1px solid rgba(168,85,247,0.4); }
.mode-partial { background: rgba(34,211,238,0.15); color: #22D3EE; border: 1px solid rgba(34,211,238,0.35); }
.mode-free    { background: rgba(100,116,139,0.2); color: #94A3B8; border: 1px solid rgba(100,116,139,0.3); }

.timer { font-size: 18px; font-weight: 700; color: #22D3EE; font-variant-numeric: tabular-nums; letter-spacing: 1px; }
.timer.overtime { color: #F87171; }
.duration-warn {
  font-size: 11px;
  color: #FBBF24;
  border: 1px solid rgba(251, 191, 36, 0.35);
  border-radius: 999px;
  padding: 2px 8px;
}

/* ── Main area ── */
.main-area {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 0;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.left-stack {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

/* ── Transcript panel ── */
.transcript-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 16px 20px;
  border-right: 1px solid rgba(34,211,238,0.1);
  overflow: hidden;
  min-height: 0;
}
.transcript-panel.compact {
  flex: 0 0 140px;
  border-top: 1px solid rgba(34,211,238,0.14);
  border-right: 1px solid rgba(34,211,238,0.1);
  background: rgba(2, 8, 23, 0.72);
  padding: 10px 14px;
}
.panel-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; font-weight: 600; color: #64748B; text-transform: uppercase;
  letter-spacing: 1px; margin-bottom: 12px; flex-shrink: 0;
}
.dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #475569; transition: all 0.3s;
}
.dot.active { background: #22C55E; box-shadow: 0 0 8px #22C55E; animation: blink 1.2s ease-in-out infinite; }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.transcript-scroll {
  flex: 1; overflow-y: auto; line-height: 1.7; font-size: 14px;
  padding-right: 8px;
}
.transcript-scroll::-webkit-scrollbar { width: 4px; }
.transcript-scroll::-webkit-scrollbar-thumb { background: rgba(34,211,238,0.3); border-radius: 2px; }
.empty-hint { color: #475569; font-size: 14px; }
.final-text  { color: #E2E8F0; }
.interim-text { color: #64748B; font-style: italic; }
.warn-box {
  margin-top: 12px; padding: 10px 14px; border-radius: 8px;
  background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3);
  color: #FCD34D; font-size: 13px;
}
.err-box {
  background: rgba(239,68,68,0.1); border-color: rgba(239,68,68,0.35); color: #FCA5A5;
}

/* ── Response panel ── */
.response-panel {
  display: flex; flex-direction: column; overflow: hidden;
  background: rgba(15,23,42,0.6); padding: 16px;
}

.resp-card {
  background: rgba(15,23,42,0.8);
  border: 1px solid var(--ac);
  border-radius: 12px; padding: 16px;
  box-shadow: 0 0 20px rgba(0,0,0,0.4), inset 0 0 20px rgba(0,0,0,0.2);
  margin-bottom: 16px;
}
.resp-agent {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 700; color: var(--ac);
  text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px;
}
.resp-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--ac); animation: blink 1s infinite;
}
.resp-text { font-size: 15px; line-height: 1.7; color: #E2E8F0; }

.resp-empty {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; color: #334155; gap: 8px;
}
.resp-empty-icon { font-size: 36px; opacity: 0.5; }
.resp-empty p { font-size: 13px; }
.merge-hint {
  margin: 0 0 10px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px dashed rgba(250, 204, 21, 0.45);
  background: rgba(250, 204, 21, 0.08);
  color: #fde68a;
  font-size: 12px;
  line-height: 1.4;
}

.candidate-wrap {
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid rgba(34,211,238,0.16);
  border-radius: 10px;
  background: rgba(2, 8, 23, 0.65);
}
.candidate-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.candidate-btn {
  text-align: left;
  padding: 9px 10px;
  border-radius: 8px;
  border: 1px solid rgba(34,211,238,0.22);
  background: rgba(30, 41, 59, 0.45);
  color: #cbd5e1;
  font-size: 12px;
  line-height: 1.4;
  cursor: pointer;
}
.candidate-btn:hover {
  border-color: rgba(34,211,238,0.42);
  color: #e2e8f0;
}

/* Session log */
.session-log { flex: 1; overflow-y: auto; border-top: 1px solid rgba(34,211,238,0.1); padding-top: 12px; }
.log-title { font-size: 11px; color: #475569; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }
.log-item { display: flex; gap: 8px; margin-bottom: 8px; font-size: 13px; line-height: 1.5; }
.log-who { font-weight: 600; white-space: nowrap; flex-shrink: 0; }
.log-text { color: #94A3B8; }

/* ── Student Stage ── */
.student-stage {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  padding: 12px 24px;
  border-top: 1px solid rgba(34,211,238,0.1);
  background: linear-gradient(180deg, rgba(5,11,24,0) 0%, rgba(15,23,42,0.6) 100%);
  flex-shrink: 0;
  height: 130px;
}
.student-stage.with-ppt {
  height: 110px;
  padding-top: 6px;
}
.student-stage :deep(.student-wrap) {
  transform: scale(0.5);
  transform-origin: center bottom;
}

/* ── Control Bar ── */
.ctrl-bar {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  padding: 10px 20px 14px;
  border-top: 1px solid rgba(34,211,238,0.1);
  background: rgba(5,11,24,0.95);
  flex-shrink: 0;
}

.mic-btn {
  display: flex; align-items: center; gap: 10px; position: relative;
  padding: 12px 32px; border-radius: 40px; border: 2px solid rgba(34,211,238,0.4);
  background: rgba(34,211,238,0.08); color: #22D3EE;
  font-size: 15px; font-weight: 600; cursor: pointer;
  transition: all 0.25s; letter-spacing: 0.5px;
}
.mic-btn:hover:not(:disabled) {
  background: rgba(34,211,238,0.15); box-shadow: 0 0 24px rgba(34,211,238,0.25);
}
.mic-btn.recording {
  background: rgba(239,68,68,0.12); border-color: rgba(239,68,68,0.5); color: #F87171;
  animation: mic-glow 2s ease-in-out infinite;
}
@keyframes mic-glow {
  0%,100% { box-shadow: 0 0 12px rgba(239,68,68,0.2); }
  50%      { box-shadow: 0 0 28px rgba(239,68,68,0.45); }
}
.mic-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.rec-pulse {
  position: absolute; right: 14px; top: 50%; transform: translateY(-50%);
  width: 8px; height: 8px; border-radius: 50%;
  background: #EF4444; animation: blink 1s ease-in-out infinite;
}
.ctrl-hint { font-size: 12px; color: #475569; }

/* ── PPT Panel ── */
.ppt-panel {
  flex-shrink: 0;
  height: 240px;
  border-top: 1px solid rgba(168,85,247,0.2);
  display: flex;
  flex-direction: column;
}
.ppt-panel.in-main {
  flex: 1;
  min-height: 0;
  height: auto;
  border-top: 0;
  border-right: 1px solid rgba(34,211,238,0.1);
}
.ppt-bar {
  display: flex; align-items: center; gap: 10px; padding: 8px 16px;
  background: rgba(168,85,247,0.08); font-size: 13px; color: #C084FC;
  border-bottom: 1px solid rgba(168,85,247,0.15); flex-shrink: 0;
}
.ppt-pages { margin-left: auto; color: #7C3AED; font-size: 12px; }
.ppt-nav {
  background: rgba(168,85,247,0.15); border: 1px solid rgba(168,85,247,0.3); color: #C084FC;
  width: 26px; height: 26px; border-radius: 6px; cursor: pointer; font-size: 16px;
  display: flex; align-items: center; justify-content: center;
}
.ppt-nav:hover { background: rgba(168,85,247,0.3); }
.ppt-view {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #0b1220;
}
.ppt-canvas {
  display: block;
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  background: #0b1220;
}
.ppt-pdf-error {
  padding: 8px 12px;
  font-size: 12px;
  color: #FCA5A5;
  text-align: center;
}
.ppt-placeholder { text-align: center; color: #475569; }
.ppt-placeholder p { margin: 4px 0; font-size: 14px; }
.ppt-hint { font-size: 12px; color: #334155; }

/* ── Transitions ── */
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.35s ease; }
.slide-up-enter-from { opacity: 0; transform: translateY(12px); }
.slide-up-leave-to   { opacity: 0; transform: translateY(-6px); }

.fade-enter-active, .fade-leave-active { transition: opacity 0.25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ── 视觉同意弹窗 ── */
.visual-consent-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0, 0, 0, 0.65);
  display: flex; align-items: center; justify-content: center;
  padding: 16px;
}
.visual-consent-modal {
  background: #0F172A;
  border: 1px solid #1E3A5F;
  border-radius: 16px;
  padding: 32px 28px;
  max-width: 440px;
  width: 100%;
  box-shadow: 0 24px 64px rgba(0,0,0,0.6);
}
.vcm-icon { font-size: 36px; text-align: center; margin-bottom: 12px; }
.vcm-title {
  font-size: 20px; font-weight: 700;
  color: #E2E8F0; text-align: center;
  margin: 0 0 12px;
}
.vcm-body {
  font-size: 14px; color: #94A3B8;
  line-height: 1.6; margin: 0 0 16px;
}
.vcm-body strong { color: #E2E8F0; }
.vcm-list {
  list-style: none; padding: 0; margin: 0 0 24px;
}
.vcm-list li {
  font-size: 13px; color: #64748B;
  padding: 4px 0 4px 20px;
  position: relative;
}
.vcm-list li::before {
  content: '✓'; position: absolute; left: 0;
  color: #22D3EE; font-weight: 700;
}
.vcm-actions {
  display: flex; flex-direction: column; gap: 10px;
}
.vcm-btn {
  padding: 12px 20px; border-radius: 10px;
  font-size: 14px; font-weight: 600;
  cursor: pointer; border: none; transition: opacity 0.2s;
}
.vcm-btn:hover { opacity: 0.85; }
.vcm-agree {
  background: linear-gradient(135deg, #2563EB, #1D4ED8);
  color: #fff;
}
.vcm-decline {
  background: transparent;
  border: 1px solid #334155;
  color: #64748B;
}
.vcm-warning {
  font-size: 13px;
  color: #FBBF24;
  background: rgba(251, 191, 36, 0.08);
  border: 1px solid rgba(251, 191, 36, 0.25);
  border-radius: 8px;
  padding: 10px 12px;
  margin: 0 0 16px;
}
.vcm-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.visual-on-badge {
  display: inline-block;
  margin-left: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  color: #22D3EE;
  border: 1px solid rgba(34, 211, 238, 0.35);
  background: rgba(34, 211, 238, 0.08);
}
</style>
