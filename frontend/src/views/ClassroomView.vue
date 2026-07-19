<template>
  <div class="classroom-root" :class="{ 'has-ppt': !!store.uploadedPPT }">

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
        <span class="timer">{{ timerStr }}</span>
      </div>

      <button class="hdr-btn hdr-end" @click="endClass">
        结束课程
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </button>
    </div>

    <!-- ══ MAIN AREA ══ -->
    <div class="main-area" :class="{ 'with-ppt': !!store.uploadedPPT }">

      <!-- LEFT: transcript panel -->
      <div class="transcript-panel">
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
      </div>

      <!-- RIGHT: agent response panel -->
      <div class="response-panel">
        <div class="panel-title">学生响应</div>

        <transition name="slide-up">
          <div v-if="currentResp" class="resp-card" :style="{ '--ac': agentColor(currentResp.student_type) }">
            <div class="resp-agent">
              <span class="resp-dot"/>
              {{ agentLabel(currentResp.student_type) }}
            </div>
            <div class="resp-text">{{ currentResp.reply_text }}</div>
          </div>
          <div v-else class="resp-empty">
            <div class="resp-empty-icon">🎓</div>
            <p>学生正在聆听…</p>
          </div>
        </transition>

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
    <div class="student-stage" :class="{ 'with-ppt': !!store.uploadedPPT }">
      <StudentFigure
        v-for="s in students"
        :key="s.id"
        :behavior="s.behavior"
        :color="s.color"
        :name="s.name"
        :active="activeStudent === s.id"
      />
    </div>

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
      </div>
    </div>

    <!-- ══ PPT PANEL (if uploaded) ══ -->
    <div v-if="store.uploadedPPT" class="ppt-panel">
      <div class="ppt-bar">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/>
          <line x1="12" y1="17" x2="12" y2="21"/>
        </svg>
        {{ store.uploadedPPT.name }}
        <span class="ppt-pages">第 {{ pptPage }} / {{ pptTotal }} 页</span>
        <button class="ppt-nav" @click="pptPage = Math.max(1, pptPage - 1)">‹</button>
        <button class="ppt-nav" @click="pptPage = Math.min(pptTotal, pptPage + 1)">›</button>
      </div>
      <div class="ppt-view">
        <iframe
          v-if="canPreviewPptFile && pptPreviewUrl"
          class="ppt-frame"
          :src="pptPreviewUrl"
          title="PPT Preview"
        />
        <div v-else class="ppt-placeholder">
          <p>📊 {{ store.uploadedPPT.name }}</p>
          <p class="ppt-hint">当前浏览器无法直接渲染 .ppt/.pptx 原文件，需后端将 PPT 转换为可预览页面（PDF/图片）后展示。</p>
          <p class="ppt-hint">{{ currentPptTextDisplay }}</p>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLessonStore } from '@/stores/lessonStore'
import { postInclassUtterance, fetchStudentState, postInclassSegment } from '@/api/ai'
import StudentFigure from '@/components/classroom/StudentFigure.vue'
import { XfyunASRClient, isXfyunSupported } from '@/api/xfyunAsr'

const router  = useRouter()
const route   = useRoute()
const store   = useLessonStore()
const currentSessionId = computed(() => String(route.params.sessionId || store.sessionId || ''))

// ── Students cast ──
const STUDENT_BASE_CAST = [
  { id: 'student_xm', name: '小明', color: '#A855F7', behavior: 'writing' },
  { id: 'student_xw', name: '小闻', color: '#22D3EE', behavior: 'dreaming' },
  { id: 'student_xw2', name: '小王', color: '#60A5FA', behavior: 'dozing' },
  { id: 'student_xl', name: '小乐', color: '#34D399', behavior: 'whisper-left' },
]
const students = ref(STUDENT_BASE_CAST.map((s) => ({ ...s })))

// ── Voice state ──
const asrSupported  = ref(isXfyunSupported())
const isRecording   = ref(false)
const transcript    = ref('')
const interimText   = ref('')
const scrollEl      = ref(null)
const micError      = ref('')   // permission / unsupported error message

// ── Supervisor / Agent state ──
const currentResp   = ref(null)
const activeStudent = ref(null)
const sessionLog    = ref([])
const chatHistory   = ref([])
const candidateEvents = ref([])
const candidatePool = ref({})
const segmentEvalResults = ref([])
const supervisorQueue = []
let supervisorBusy = false
let sentenceBuffer = ''
let clearRespTimer = null
const latestQuestioningEvents = ref([])

// ── Segment (send to backend) ──
const THREE_MIN_MS = 3 * 60 * 1000
let segmentSeq = 1
let currentSegment = null

// ── Timer ──
const elapsedSec    = ref(0)
let timerInterval   = null
const timerStr = computed(() => {
  const m = Math.floor(elapsedSec.value / 60).toString().padStart(2, '0')
  const s = (elapsedSec.value % 60).toString().padStart(2, '0')
  return `${m}:${s}`
})

// ── Mode badge ──
const modeLabel = computed(() => {
  const hasBoth  = store.uploadedLesson && store.uploadedPPT
  const hasLesson = !!store.uploadedLesson
  const hasPPT    = !!store.uploadedPPT
  if (hasBoth)   return '教案 + PPT 模式'
  if (hasLesson) return '教案模式'
  if (hasPPT)    return 'PPT 模式'
  return '自由模式'
})
const modeCls = computed(() => {
  if (store.uploadedLesson && store.uploadedPPT) return 'mode-full'
  if (store.uploadedLesson || store.uploadedPPT)  return 'mode-partial'
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
const canPreviewPptFile = computed(() => {
  const file = store.uploadedPPT
  if (!file) return false
  return file.type === 'application/pdf' || /\.pdf$/i.test(file.name || '')
})
watch(pptPage, async (newPage, oldPage) => {
  if (!store.uploadedPPT || newPage === oldPage) return
  if (isRecording.value && currentSegment) {
    await flushCurrentSegment('ppt_page_switch')
  }
  startNewSegment()
})
watch(
  () => store.uploadedPPT,
  (file) => {
    if (pptPreviewUrl.value) {
      URL.revokeObjectURL(pptPreviewUrl.value)
      pptPreviewUrl.value = ''
    }
    if (file && (file.type === 'application/pdf' || /\.pdf$/i.test(file.name || ''))) {
      pptPreviewUrl.value = URL.createObjectURL(file)
    }
  },
  { immediate: true }
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
  return p1.test(t) || p2.test(t) || p3.test(t)
}

function buildCurrentPptText() {
  const slides = store.analysisResult?._raw?.slides
  if (!Array.isArray(slides)) return '当前未获取到PPT文本内容'
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

function stopTimer() {
  clearInterval(timerInterval)
  timerInterval = null
}

function nowIso() {
  return new Date().toISOString()
}

function currentSlideNo() {
  return store.uploadedPPT ? pptPage.value : 0
}

function startNewSegment() {
  currentSegment = {
    segment_id: `seg-${Date.now()}-${segmentSeq++}`,
    start_ts: nowIso(),
    start_ms: Date.now(),
    slide_no: currentSlideNo(),
    teacher_utterances: [],
    student_utterances: [],
  }
}

function normalizeEvent(evt) {
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

function flushResidualSentence() {
  const rest = sentenceBuffer.trim()
  sentenceBuffer = ''
  if (rest) handleTeacherSentence(rest, nowIso())
}

function appendTranscript(text) {
  if (!text?.trim()) return
  micError.value = ''
  interimText.value = ''
  transcript.value += text

  nextTick(() => {
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  })

  const completed = consumeCompletedSentences(text)
  completed.forEach((sentence) => handleTeacherSentence(sentence, nowIso()))
}

function buildXfyunClient() {
  return new XfyunASRClient({
    onText: appendTranscript,
    onError: (message) => {
      console.warn('[XFYUN ASR] error:', message)
      isRecording.value = false
      stopTimer()
      micError.value = `❌ ${message}`
    },
    onClose: () => {
      if (isRecording.value) {
        isRecording.value = false
        stopTimer()
      }
    },
  })
}

function enqueueTeacherSentence(task) {
  supervisorQueue.push(task)
  processSupervisorQueue()
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
        role: task.role,
        content: task.content,
        called_student_id: task.called_student_id || null,
        current_ppt: buildCurrentPptPayload(),
      }

      let result = null
      try {
        result = await postInclassUtterance(payload)
      } catch {
        result = null
      }

      // 后端未就绪时，问题句使用预设6候选兜底
      if (!result && task.role === 'teacher' && looksQuestioning(task.content)) {
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

  if (Array.isArray(result.student_event)) {
    const normalized = result.student_event.map(normalizeEvent).filter(Boolean)
    latestQuestioningEvents.value = normalized

    const nextPool = {}
    for (const evt of normalized) {
      if (!nextPool[evt.student_type]) nextPool[evt.student_type] = []
      nextPool[evt.student_type].push(evt)
    }
    candidatePool.value = nextPool

    candidateEvents.value = normalized.slice(0, 6).map((evt) => ({ ...evt }))
    return
  }

  const one = normalizeEvent(result.student_event)
  if (!one) return
  if (one.is_triggered || result.should_trigger_student) {
    await playStudentEvent(one)
    candidateEvents.value = []
  } else {
    candidateEvents.value = [one]
  }
}

function findStudentById(id) {
  return students.value.find((s) => s.id === id) || null
}

async function handleTeacherSentence(text, ts) {
  if (!text) return
  if (!currentSegment) startNewSegment()

  const calledStudent = detectCalledStudent(text)
  const calledId = calledStudent?.student_id || null
  const pointing = isPointingSentence(text, calledStudent)

  currentSegment.teacher_utterances.push({ speaker: 'teacher', ts, text })
  appendChat('teacher', text, ts, calledId)

  // 点名句 + 已有预设候选：前端直接挑选并播放，不交 supervisor
  if (pointing && latestQuestioningEvents.value.length) {
    const state = await getStudentStateFromBackend(calledId)
    const chosen = pickPresetForCalledStudent(latestQuestioningEvents.value, state)
    if (chosen) {
      const studentMeta = findStudentById(calledId)
      await playStudentEvent({
        ...chosen,
        student_id: calledId,
        student_name: studentMeta?.name || calledStudent?.student_name || '学生',
        academic_type: chosen.student_type,
      })
      if (!store.uploadedPPT && Date.now() - currentSegment.start_ms >= THREE_MIN_MS) {
        flushCurrentSegment('no_ppt_3min_sentence_complete')
      }
      return
    }
  }
  // 其他句子：正常交后端（后端自行决定是否调用 supervisor）
  enqueueTeacherSentence({
    role: 'teacher',
    content: text,
    current_timestamp: ts,
    called_student_id: calledId,
  })

  if (!store.uploadedPPT && Date.now() - currentSegment.start_ms >= THREE_MIN_MS) {
    flushCurrentSegment('no_ppt_3min_sentence_complete')
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

  const ts = nowIso()
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
    role: resp.student_name || '学生',
    content: resp.reply_text,
    current_timestamp: ts,
    called_student_id: null,
  })

  speak(resp.reply_text, resp.student_type)

  clearTimeout(clearRespTimer)
  const delay = Math.max(3000, resp.reply_text.length * 280 + 1500)
  clearRespTimer = setTimeout(() => {
    currentResp.value = null
    activeStudent.value = null
  }, delay)
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

// ── TTS ──
function speak(text, agentType) {
  if (!window.speechSynthesis) return
  window.speechSynthesis.cancel()

  const u = new SpeechSynthesisUtterance(text)
  u.lang = 'zh-CN'

  switch (agentType) {
    case 'gangjing': u.pitch = 1.25; u.rate = 1.1;  break
    case 'xuekun':   u.pitch = 0.85; u.rate = 0.88; break
    case 'sleepy':   u.pitch = 0.70; u.rate = 0.80; break
    case 'whisper':  u.pitch = 1.00; u.rate = 0.95; u.volume = 0.65; break
    default:         u.pitch = 1.00; u.rate = 0.95
  }

  window.speechSynthesis.speak(u)
}

// ── Controls ──
async function toggleRecording() {
  if (!asrSupported.value) return
  micError.value = ''

  if (isRecording.value) {
    // — STOP —
    isRecording.value = false
    stopTimer()
    asrClient?.stop()
    flushResidualSentence()
    await flushCurrentSegment('manual_stop')
    window.speechSynthesis.cancel()
    return
  }

  try {
    asrClient = buildXfyunClient()
    await asrClient.start()
    isRecording.value = true
    chatHistory.value = []
    candidateEvents.value = []
    candidatePool.value = {}
    latestQuestioningEvents.value = []
    if (!currentSegment) startNewSegment()
    stopTimer()  // clear any stale interval before starting a new one
    timerInterval = setInterval(() => elapsedSec.value++, 1000)
  } catch (err) {
    const message = err?.message || '未知错误'
    if (message.includes('未配置')) {
      micError.value = '❌ 讯飞Key未配置：请在项目根目录 .env 添加 VITE_XFYUN_APP_ID / VITE_XFYUN_API_KEY / VITE_XFYUN_API_SECRET。'
    } else if (message.includes('Permission denied') || message.includes('denied')) {
      micError.value = '❌ 麦克风权限被拒绝，请点击地址栏左侧锁图标允许麦克风访问后重试。'
    } else {
      micError.value = `❌ 无法启动讯飞语音识别：${message}`
    }
  }
}

function endClass() {
  asrClient?.stop()
  stopTimer()
  flushResidualSentence()
  flushCurrentSegment('end_class')
  window.speechSynthesis.cancel()
  router.push(`/report/${currentSessionId.value}`)
}

onUnmounted(() => {
  asrClient?.stop()
  stopTimer()
  clearTimeout(clearRespTimer)
  window.speechSynthesis.cancel()
  if (pptPreviewUrl.value) {
    URL.revokeObjectURL(pptPreviewUrl.value)
    pptPreviewUrl.value = ''
  }
})

startNewSegment()
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

/* ── Main area ── */
.main-area {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 0;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ── Transcript panel ── */
.transcript-panel {
  display: flex;
  flex-direction: column;
  padding: 16px 20px;
  border-right: 1px solid rgba(34,211,238,0.1);
  overflow: hidden;
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
  flex: 1; overflow-y: auto; line-height: 1.9; font-size: 16px;
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
  height: 180px;
}
.student-stage.with-ppt {
  height: 150px;
  padding-top: 6px;
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
.ppt-panel { flex-shrink: 0; height: 240px; border-top: 1px solid rgba(168,85,247,0.2); display: flex; flex-direction: column; }
.classroom-root.has-ppt .main-area {
  flex: 0 0 32%;
}
.classroom-root.has-ppt .ppt-panel {
  height: 320px;
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
.ppt-view { flex: 1; display: flex; align-items: center; justify-content: center; }
.ppt-frame {
  width: 100%;
  height: 100%;
  border: 0;
  background: #0b1220;
}
.ppt-placeholder { text-align: center; color: #475569; }
.ppt-placeholder p { margin: 4px 0; font-size: 14px; }
.ppt-hint { font-size: 12px; color: #334155; }

/* ── Transitions ── */
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.35s ease; }
.slide-up-enter-from { opacity: 0; transform: translateY(12px); }
.slide-up-leave-to   { opacity: 0; transform: translateY(-6px); }
</style>
