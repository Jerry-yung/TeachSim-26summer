import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { analyzeLesson, DEFAULT_INTERVIEW_QUESTIONS } from '@/mock/aiQuestions.js'
import {
  initLessonBootstrap,
  parseLessonFile,
  parseLessonFiles,
  fetchLatestPreset,
  fetchAbilityProfile,
} from '@/api/ai.js'

const DISCIPLINE_SIMULATION_QUESTION = {
  id: 'discipline_simulation_level',
  type: 'radio',
  label: '课堂纪律事件模拟强度（睡觉/交头接耳）',
  emoji: '🚨',
  required: false,
  skippable: true,
  options: ['高频（重点训练）', '中频', '低频', '关闭（不触发）'],
}

const DISCIPLINE_SIMULATION_PROFILES = {
  '高频（重点训练）': {
    enabled: true,
    start_after_s: 120,
    tick_interval_s: 60,
    trigger_probability_per_tick: 0.15,
    event_cooldown_s: 60,
    max_concurrent_events: 1,
    block_while_student_speaking: true,
    block_while_deferred_round_active: true,
    event_weights: { sleep: 0.5, whisper: 0.5 },
  },
  '中频': {
    enabled: true,
    start_after_s: 180,
    tick_interval_s: 90,
    trigger_probability_per_tick: 0.1,
    event_cooldown_s: 90,
    max_concurrent_events: 1,
    block_while_student_speaking: true,
    block_while_deferred_round_active: true,
    event_weights: { sleep: 0.5, whisper: 0.5 },
  },
  '低频': {
    enabled: true,
    start_after_s: 300,
    tick_interval_s: 120,
    trigger_probability_per_tick: 0.05,
    event_cooldown_s: 120,
    max_concurrent_events: 1,
    block_while_student_speaking: true,
    block_while_deferred_round_active: true,
    event_weights: { sleep: 0.5, whisper: 0.5 },
  },
  '关闭（不触发）': {
    enabled: false,
    start_after_s: null,
    tick_interval_s: 10,
    trigger_probability_per_tick: 0,
    event_cooldown_s: null,
    max_concurrent_events: 0,
    block_while_student_speaking: true,
    block_while_deferred_round_active: true,
    event_weights: { sleep: 0.5, whisper: 0.5 },
  },
}

const DISCIPLINE_PUSH_CONFIG = {
  threshold_per_lesson: 0.5,
  level_weight: {
    '高频（重点训练）': 0.7,
    '中频': 0.5,
    '低频': 0.35,
  },
  level_cap: {
    '高频（重点训练）': 0.45,
    '中频': 0.3,
    '低频': 0.22,
  },
}

function ensureDisciplineQuestion(questions = []) {
  const list = Array.isArray(questions) ? [...questions] : []
  if (!list.some((q) => q?.id === DISCIPLINE_SIMULATION_QUESTION.id)) {
    list.push(DISCIPLINE_SIMULATION_QUESTION)
  }
  return list
}

const LESSON_STORE_CACHE_KEY = 'teachsim_lesson_store_v1'

function loadCachedLessonState() {
  try {
    const raw = localStorage.getItem(LESSON_STORE_CACHE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return null
    return parsed
  } catch {
    return null
  }
}

function saveCachedLessonState(payload) {
  try {
    localStorage.setItem(LESSON_STORE_CACHE_KEY, JSON.stringify(payload))
  } catch {
    // ignore storage quota / private mode errors
  }
}

function clearCachedLessonState() {
  try {
    localStorage.removeItem(LESSON_STORE_CACHE_KEY)
  } catch {
    // ignore
  }
}

export const useLessonStore = defineStore('lesson', () => {
  const uploadedLesson = ref(null)
  const uploadedPPT = ref(null)
  const teacherContext = ref('')
  const isAnalyzing = ref(false)
  const isBootstrapping = ref(false)
  const analysisResult = ref(null)
  const lessonId = ref(null)
  const sessionId = ref(null)

  const currentQuestionIndex = ref(0)
  const interviewAnswers = ref({})
  const interviewDirection = ref('forward')
  const restoringFromCache = ref(false)
  const abilityDisciplineEventsPerLesson = ref(null)

  // 记录「刷新前有哪类文件」，用于恢复模式标签（File 对象本身无法序列化）
  const hadLessonFile = ref(false)
  const hadPptFile = ref(false)

  function persistState() {
    if (restoringFromCache.value) return
    saveCachedLessonState({
      teacherContext: teacherContext.value || '',
      analysisResult: analysisResult.value || null,
      lessonId: lessonId.value || null,
      sessionId: sessionId.value || null,
      currentQuestionIndex: Number(currentQuestionIndex.value || 0),
      interviewAnswers: interviewAnswers.value || {},
      interviewDirection: interviewDirection.value || 'forward',
      hadLessonFile: uploadedLesson.value !== null || hadLessonFile.value,
      hadPptFile: uploadedPPT.value !== null || hadPptFile.value,
    })
  }

  function restoreStateFromCache() {
    const cached = loadCachedLessonState()
    if (!cached) return
    restoringFromCache.value = true
    teacherContext.value = String(cached.teacherContext || '')
    analysisResult.value = cached.analysisResult || null
    lessonId.value = cached.lessonId || null
    sessionId.value = cached.sessionId || null
    currentQuestionIndex.value = Math.max(0, Number(cached.currentQuestionIndex || 0))
    interviewAnswers.value = cached.interviewAnswers || {}
    interviewDirection.value = String(cached.interviewDirection || 'forward')
    hadLessonFile.value = Boolean(cached.hadLessonFile)
    hadPptFile.value = Boolean(cached.hadPptFile)
    restoringFromCache.value = false
  }

  restoreStateFromCache()

  watch(
    [
      teacherContext,
      analysisResult,
      lessonId,
      sessionId,
      currentQuestionIndex,
      interviewAnswers,
      interviewDirection,
    ],
    () => persistState(),
    { deep: true },
  )

  const hasAnyFile = computed(
    () => uploadedLesson.value !== null || uploadedPPT.value !== null,
  )
  const canStart = computed(() => !isAnalyzing.value && !isBootstrapping.value)

  function _extractFromContext(text) {
    if (!text) return {}
    const known = {}

    const GRADE_MAP = [
      ['高三', '高三'], ['高二', '高二'], ['高一', '高一'],
      ['初三', '初三'], ['初二', '初二'], ['初一', '初一'],
      ['大学|大一|大二|大三|大四', '大学'],
      ['幼儿园|幼小|学前', '幼儿园'],
      ['小学|一年级|二年级|三年级|四年级|五年级|六年级', '小学'],
    ]
    for (const [re, val] of GRADE_MAP) {
      if (new RegExp(re).test(text)) { known.grade = val; break }
    }

    if (/重点班/.test(text)) known.class_level = '重点班'
    else if (/普通班|平行班/.test(text)) known.class_level = '普通班'
    else if (/实验班/.test(text)) known.class_level = '重点班'

    if (/数学/.test(text)) known.subject = '数学'
    else if (/语文/.test(text)) known.subject = '语文'
    else if (/英语|外语/.test(text)) known.subject = '英语'
    else if (/物理/.test(text)) known.subject = '物理'
    else if (/化学/.test(text)) known.subject = '化学'
    else if (/生物/.test(text)) known.subject = '生物'
    else if (/历史/.test(text)) known.subject = '历史'
    else if (/地理/.test(text)) known.subject = '地理'
    else if (/政治|思政/.test(text)) known.subject = '政治'

    if (/40\s*分|40min/i.test(text)) known.duration = '40 分钟'
    else if (/45\s*分|45min/i.test(text)) known.duration = '45 分钟'
    else if (/50\s*分|50min/i.test(text)) known.duration = '50 分钟'
    else if (/一节课|单节课/.test(text)) known.duration = '45 分钟'
    else if (/30\s*分|30min/i.test(text)) known.duration = '30 分钟'
    else if (/60\s*分|60min|一小时/i.test(text)) known.duration = '60 分钟'

    if (/基础较?(差|弱|薄|低)|从零|零基础/.test(text)) known.student_level = '较弱：从零开始，需要基础性引导'
    else if (/基础(好|扎实|强|牢固)|优秀/.test(text)) known.student_level = '扎实：大多数同学有充分的前置基础'
    else if (/中等|一般/.test(text)) known.student_level = '中等：部分同学有基础，部分较薄弱'

    if (/节奏/.test(text)) known.practice_focus = '课堂节奏把控'
    else if (/互动|提问/.test(text)) known.practice_focus = '提问质量与互动引导'
    else if (/衔接|过渡/.test(text)) known.practice_focus = '知识点衔接流畅度'
    else if (/语言|表达/.test(text)) known.practice_focus = '语言表达与亲和力'
    else if (/时间|分配/.test(text)) known.practice_focus = '时间分配合理性'

    return known
  }

  const contextKnown = computed(() => _extractFromContext(teacherContext.value))

  const interviewQuestions = computed(() => {
    const raw = ensureDisciplineQuestion(
      analysisResult.value?.teacher_questions ?? DEFAULT_INTERVIEW_QUESTIONS,
    )
    if (!teacherContext.value) return raw

    const known = _extractFromContext(teacherContext.value)

    return raw.filter((q) => {
      if (q.id === 'grade' && known.grade) return false
      if (q.id === 'class_level' && known.class_level) return false
      if (q.id === 'duration' && known.duration) return false
      if (q.id === 'student_level' && known.student_level) return false
      if (q.id === 'practice_focus' && known.practice_focus) return false
      return true
    })
  })

  const totalQuestions = computed(() => interviewQuestions.value.length)
  const currentQuestion = computed(
    () => interviewQuestions.value[currentQuestionIndex.value] ?? null,
  )
  const isInterviewComplete = computed(
    () => currentQuestionIndex.value >= totalQuestions.value,
  )
  const interviewProgress = computed(() =>
    totalQuestions.value > 0
      ? Math.round((currentQuestionIndex.value / totalQuestions.value) * 100)
      : 0,
  )

  const evaluationDimensions = computed(() => {
    const dims = []
    const push = (k, label, source) => {
      if (!dims.some((d) => d.key === k && d.label === label)) {
        dims.push({ key: k, label, source })
      }
    }

    const goals = interviewAnswers.value.lesson_goal
    if (Array.isArray(goals)) goals.forEach((g) => push('lesson_goal', g, 'interview'))
    else if (goals) push('lesson_goal', goals, 'interview')

    const focuses = interviewAnswers.value.practice_focus
    if (Array.isArray(focuses)) focuses.forEach((f) => push('practice_focus', f, 'interview'))
    else if (focuses) push('practice_focus', focuses, 'interview')

    if (interviewAnswers.value.student_level) {
      push('student_level', interviewAnswers.value.student_level, 'interview')
    }
    if (interviewAnswers.value.atmosphere) {
      push('atmosphere', interviewAnswers.value.atmosphere, 'interview')
    }

    return dims
  })

  const disciplineSimulationLevel = computed(() =>
    _firstValue(interviewAnswers.value.discipline_simulation_level, '关闭（不触发）'),
  )

  function applyDisciplinePushProfile(baseProfile, level) {
    const profile = { ...(baseProfile || {}) }
    if (!profile.enabled || level === '关闭（不触发）') {
      profile.trigger_probability_per_tick = 0
      return profile
    }
    const baseP = Number(profile.trigger_probability_per_tick || 0)
    const avg = Number(abilityDisciplineEventsPerLesson.value)
    if (!Number.isFinite(avg)) return profile
    const threshold = Number(DISCIPLINE_PUSH_CONFIG.threshold_per_lesson || 0.5)
    if (!(avg < threshold)) return profile

    const gap = Math.max(0, Math.min(1, (threshold - avg) / Math.max(threshold, 0.0001)))
    const weight = Number(DISCIPLINE_PUSH_CONFIG.level_weight[level] || 0)
    const cap = Number(DISCIPLINE_PUSH_CONFIG.level_cap[level] || baseP)
    const delta = baseP * gap * weight
    profile.trigger_probability_per_tick = Math.max(0, Math.min(cap, baseP + delta))
    return profile
  }

  const disciplineSimulationProfile = computed(() =>
    applyDisciplinePushProfile(
      DISCIPLINE_SIMULATION_PROFILES[disciplineSimulationLevel.value]
      || DISCIPLINE_SIMULATION_PROFILES['关闭（不触发）'],
      disciplineSimulationLevel.value,
    ),
  )

  async function preloadAbilityDisciplineProfile() {
    try {
      const data = await fetchAbilityProfile()
      const sections = Array.isArray(data?.sections) ? data.sections : []
      let found = null
      for (const section of sections) {
        const metrics = Array.isArray(section?.metrics) ? section.metrics : []
        const one = metrics.find((m) => String(m?.key || '') === 'discipline_events_per_lesson')
        if (one) {
          found = Number(one.value)
          break
        }
      }
      abilityDisciplineEventsPerLesson.value = Number.isFinite(found) ? found : null
    } catch {
      abilityDisciplineEventsPerLesson.value = null
    }
  }

  async function uploadLessonFile(file) {
    uploadedLesson.value = file
    sessionId.value = null
    lessonId.value = null
    await _triggerAnalysis()
  }

  async function uploadPPTFile(file) {
    uploadedPPT.value = file
    sessionId.value = null
    lessonId.value = null
    await _triggerAnalysis()
  }

  async function _triggerAnalysis() {
    // 新一轮分析开始时，用当前实际上传的文件重置标志，防止旧标志污染新课堂
    hadLessonFile.value = uploadedLesson.value !== null
    hadPptFile.value = uploadedPPT.value !== null
    isAnalyzing.value = true
    analysisResult.value = null
    try {
      let result
      const bothFiles = uploadedLesson.value && uploadedPPT.value
      if (bothFiles) {
        result = await parseLessonFiles([uploadedLesson.value, uploadedPPT.value])
      } else {
        const file = uploadedLesson.value || uploadedPPT.value
        result = await parseLessonFile(file)
      }
      analysisResult.value = _adaptAIResult(result)
      lessonId.value = `lesson-${Date.now()}`
    } catch (err) {
      console.warn('[AI] 真实接口调用失败，回退到 mock：', err.message)
      const file = uploadedLesson.value || uploadedPPT.value
      try {
        const mockResult = await analyzeLesson(file)
        analysisResult.value = mockResult
        lessonId.value = `lesson-${Date.now()}`
      } catch {
        analysisResult.value = null
      }
    } finally {
      isAnalyzing.value = false
    }
  }

  function _adaptAIResult(raw) {
    const info = raw.basic_info ?? {}
    const kps = raw.knowledge_points ?? []
    return {
      lesson_topic: info.lesson_topic ?? '未知课题',
      subject: info.subject ?? '通用',
      subject_icon: _guessSubjectIcon(info.subject ?? ''),
      knowledge_points_preview: kps.slice(0, 3).map((k) => k.point),
      teacher_questions: raw.teacher_questions ?? DEFAULT_INTERVIEW_QUESTIONS,
      _raw: raw,
    }
  }

  function _guessSubjectIcon(subject) {
    if (subject.includes('数学')) return '🔢'
    if (subject.includes('语文') || subject.includes('文学')) return '📖'
    if (subject.includes('英语') || subject.includes('外语')) return '🌍'
    if (subject.includes('物理')) return '⚛️'
    if (subject.includes('化学')) return '🧪'
    if (subject.includes('生物')) return '🧬'
    if (subject.includes('历史')) return '🏛️'
    if (subject.includes('地理')) return '🗺️'
    if (subject.includes('政治') || subject.includes('道德')) return '⚖️'
    if (subject.includes('音乐')) return '🎵'
    if (subject.includes('美术') || subject.includes('艺术')) return '🎨'
    if (subject.includes('体育')) return '⚽'
    return '📚'
  }

  function _firstValue(val, fallback = '') {
    if (Array.isArray(val)) return val[0] || fallback
    return val || fallback
  }

  function _normalizedClassLevel(raw) {
    if (raw === '重点班') return '重点班'
    if (raw === '平行班') return '平行班'
    return '普通班'
  }

  function _normalizedAtmosphere(raw) {
    if (raw === '活跃互动型') return '活跃'
    if (raw === '均衡参与型') return '均衡'
    if (raw === '沉浸讲解型' || raw === '沉浸讲授型') return '沉闷'
    // 课前问卷历史/兼容
    if (raw === '严谨讨论型' || raw === '练习主导型') return '活跃'
    if (raw === '活跃' || raw === '沉闷' || raw === '均衡') return raw
    return '沉闷'
  }

  function _prefsMultiField(raw, fallback) {
    if (Array.isArray(raw) && raw.length) {
      return raw.map((x) => String(x).trim()).filter(Boolean)
    }
    if (raw != null && String(raw).trim()) return String(raw).trim()
    return fallback
  }

  function _buildTeachingPreferences() {
    const raw = analysisResult.value?._raw
    const selectedDisciplineLevel =
      _firstValue(interviewAnswers.value.discipline_simulation_level, '关闭（不触发）')
    const disciplineProfile =
      DISCIPLINE_SIMULATION_PROFILES[selectedDisciplineLevel]
      || DISCIPLINE_SIMULATION_PROFILES['关闭（不触发）']

    const studentLevel =
      _firstValue(interviewAnswers.value.student_level, contextKnown.value.student_level) || null

    return {
      duration: _firstValue(interviewAnswers.value.duration, contextKnown.value.duration || '45 分钟'),
      grade:
        _firstValue(interviewAnswers.value.grade, contextKnown.value.grade) ||
        raw?.basic_info?.grade ||
        '未填写',
      class_type: _normalizedClassLevel(
        _firstValue(interviewAnswers.value.class_level, contextKnown.value.class_level),
      ),
      primary_goal: _prefsMultiField(interviewAnswers.value.lesson_goal, '技能掌握与方法运用'),
      breakthrough_focus: _prefsMultiField(
        interviewAnswers.value.practice_focus,
        contextKnown.value.practice_focus || '提问质量与互动引导',
      ),
      ...(studentLevel ? { student_level: studentLevel } : {}),
      discipline_simulation_level: selectedDisciplineLevel,
      discipline_simulation_profile: disciplineProfile,
    }
  }

  function _buildBootstrapPayload(frontendSessionId) {
    const raw = analysisResult.value?._raw
    const teachingPreferences = _buildTeachingPreferences()
    const grade =
      _firstValue(interviewAnswers.value.grade, contextKnown.value.grade) ||
      raw?.basic_info?.grade ||
      '未填写'
    const subject =
      raw?.basic_info?.subject ||
      contextKnown.value.subject ||
      analysisResult.value?.subject ||
      '通用'
    const classLevel = _normalizedClassLevel(
      _firstValue(interviewAnswers.value.class_level, contextKnown.value.class_level),
    )
    const atmosphere = _normalizedAtmosphere(
      _firstValue(interviewAnswers.value.atmosphere, '活跃互动型'),
    )
    const practiceFocus = interviewAnswers.value.practice_focus
    const customGoal = Array.isArray(practiceFocus)
      ? practiceFocus.join('、')
      : (practiceFocus || '')

    let lessonJson = null
    let pptJson = null
    if (raw?.basic_info) {
      lessonJson = { ...raw }
    }
    if (raw?.deck_info || raw?.slides) {
      pptJson = {
        deck_info: raw.deck_info ?? null,
        slides: raw.slides ?? [],
      }
    }

    return {
      grade,
      subject,
      class_level: classLevel,
      atmosphere,
      custom_goal: customGoal,
      teacher_context: teacherContext.value,
      lesson_json: lessonJson,
      ppt_json: pptJson,
      teaching_preferences_json: teachingPreferences,
      frontend_session_id: frontendSessionId,
      // 即使已有课前解析结果，也保留原始 PPT 上传到后端：
      // 1) 课前解析继续使用前端已拿到的 ppt_json
      // 2) 后端可对原始 ppt/pptx 做预转换，课堂阶段直接读取 PDF 预览
      file: uploadedPPT.value || (lessonJson ? null : (uploadedLesson.value || null)),
    }
  }

  async function bootstrapClassroomSession(frontendSessionId) {
    isBootstrapping.value = true
    try {
      await preloadAbilityDisciplineProfile()
      const payload = _buildBootstrapPayload(frontendSessionId)
      const result = await initLessonBootstrap(payload)
      lessonId.value = result.lesson_id
      sessionId.value = result.session_id
      return result
    } finally {
      isBootstrapping.value = false
    }
  }

  function currentPptSlide(pageNo) {
    const slides = analysisResult.value?._raw?.slides
    if (!Array.isArray(slides)) return null
    return slides.find((s) => Number(s.slide_no) === Number(pageNo)) ?? null
  }

  function removeLesson() {
    uploadedLesson.value = null
    hadLessonFile.value = false
    sessionId.value = null
    lessonId.value = null
    if (!uploadedPPT.value) analysisResult.value = null
  }

  function removePPT() {
    uploadedPPT.value = null
    hadPptFile.value = false
    sessionId.value = null
    lessonId.value = null
    if (!uploadedLesson.value) analysisResult.value = null
  }

  function answerAndNext(questionId, value) {
    interviewAnswers.value = { ...interviewAnswers.value, [questionId]: value }
    interviewDirection.value = 'forward'
    currentQuestionIndex.value++
  }

  function skipQuestion() {
    interviewDirection.value = 'forward'
    currentQuestionIndex.value++
  }

  function goBack() {
    if (currentQuestionIndex.value > 0) {
      interviewDirection.value = 'backward'
      currentQuestionIndex.value--
    }
  }

  function resetInterview() {
    currentQuestionIndex.value = 0
    interviewAnswers.value = { ...contextKnown.value }
    interviewDirection.value = 'forward'
  }

  async function applyLatestPresetAnswers() {
    const data = await fetchLatestPreset()
    if (!data?.has_preset || !data?.interview_answers) return false
    const presetAnswers = data.interview_answers
    interviewAnswers.value = {
      ...contextKnown.value,
      ...presetAnswers,
    }
    interviewDirection.value = 'forward'
    currentQuestionIndex.value = totalQuestions.value
    return true
  }

  function reset() {
    uploadedLesson.value = null
    uploadedPPT.value = null
    hadLessonFile.value = false
    hadPptFile.value = false
    teacherContext.value = ''
    isAnalyzing.value = false
    isBootstrapping.value = false
    analysisResult.value = null
    lessonId.value = null
    sessionId.value = null
    resetInterview()
    clearCachedLessonState()
  }

  /**
   * 进入新一轮课前流程时调用。
   * - 清除上节课残留的 hadPptFile / hadLessonFile（当前没有实体文件时）
   * - 强制清除 sessionId，使 bootstrapClassroomSession 发起全新 session
   *   而不是复用上节课 session
   * - 若无任何文件，同时清除 lessonId / analysisResult，避免旧课 lessonId
   *   被 loadPptPreview 误认为有 PPT
   */
  function prepareNewClassroom() {
    if (!uploadedLesson.value) hadLessonFile.value = false
    if (!uploadedPPT.value)   hadPptFile.value   = false
    // 强制下一次 bootstrapClassroomSession 走新建流程
    sessionId.value = null
    if (!uploadedLesson.value && !uploadedPPT.value) {
      lessonId.value     = null
      analysisResult.value = null
    }
  }

  return {
    uploadedLesson,
    uploadedPPT,
    teacherContext,
    isAnalyzing,
    isBootstrapping,
    analysisResult,
    lessonId,
    sessionId,
    hasAnyFile,
    canStart,
    currentQuestionIndex,
    interviewAnswers,
    interviewDirection,
    interviewQuestions,
    totalQuestions,
    currentQuestion,
    hadLessonFile,
    hadPptFile,
    isInterviewComplete,
    interviewProgress,
    evaluationDimensions,
    disciplineSimulationLevel,
    disciplineSimulationProfile,
    preloadAbilityDisciplineProfile,
    uploadLessonFile,
    uploadPPTFile,
    bootstrapClassroomSession,
    currentPptSlide,
    removeLesson,
    removePPT,
    answerAndNext,
    skipQuestion,
    goBack,
    applyLatestPresetAnswers,
    resetInterview,
    reset,
    prepareNewClassroom,
    contextKnown,
  }
})
