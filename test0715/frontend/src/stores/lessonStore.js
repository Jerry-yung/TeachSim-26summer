import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { analyzeLesson, DEFAULT_INTERVIEW_QUESTIONS } from '@/mock/aiQuestions.js'
import {
  initLessonBootstrap,
  parseLessonFile,
  parseLessonFiles,
} from '@/api/ai.js'

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
    const raw = analysisResult.value?.teacher_questions ?? DEFAULT_INTERVIEW_QUESTIONS
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
    if (raw === '严谨讨论型') return '活跃'
    if (raw === '练习主导型') return '活跃'
    return '沉闷'
  }

  function _buildTeachingPreferences() {
    const raw = analysisResult.value?._raw
    return {
      duration: _firstValue(interviewAnswers.value.duration, contextKnown.value.duration || '45 分钟'),
      grade:
        _firstValue(interviewAnswers.value.grade, contextKnown.value.grade) ||
        raw?.basic_info?.grade ||
        '未填写',
      class_type: _normalizedClassLevel(
        _firstValue(interviewAnswers.value.class_level, contextKnown.value.class_level),
      ),
      primary_goal: _firstValue(interviewAnswers.value.lesson_goal, '技能掌握与方法运用'),
      breakthrough_focus: _firstValue(
        interviewAnswers.value.practice_focus,
        contextKnown.value.practice_focus || '提问质量与互动引导',
      ),
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
      file: lessonJson ? null : (uploadedLesson.value || uploadedPPT.value || null),
    }
  }

  async function bootstrapClassroomSession(frontendSessionId) {
    if (sessionId.value) return { lesson_id: lessonId.value, session_id: sessionId.value }
    isBootstrapping.value = true
    try {
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
    sessionId.value = null
    lessonId.value = null
    if (!uploadedPPT.value) analysisResult.value = null
  }

  function removePPT() {
    uploadedPPT.value = null
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

  function reset() {
    uploadedLesson.value = null
    uploadedPPT.value = null
    teacherContext.value = ''
    isAnalyzing.value = false
    isBootstrapping.value = false
    analysisResult.value = null
    lessonId.value = null
    sessionId.value = null
    resetInterview()
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
    isInterviewComplete,
    interviewProgress,
    evaluationDimensions,
    uploadLessonFile,
    uploadPPTFile,
    bootstrapClassroomSession,
    currentPptSlide,
    removeLesson,
    removePPT,
    answerAndNext,
    skipQuestion,
    goBack,
    resetInterview,
    reset,
    contextKnown,
  }
})
