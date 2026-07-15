import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { analyzeLesson, DEFAULT_INTERVIEW_QUESTIONS } from '@/mock/aiQuestions.js'

export const useLessonStore = defineStore('lesson', () => {
  // ── Setup page state ──────────────────────────────────────────────────
  const uploadedFile = ref(null)
  const teacherContext = ref('')   // 老师自由描述的教学背景
  const isAnalyzing = ref(false)
  const analysisResult = ref(null)
  const lessonId = ref(null)

  // ── Interview page state ──────────────────────────────────────────────
  const currentQuestionIndex = ref(0)
  const interviewAnswers = ref({})
  const interviewDirection = ref('forward') // 'forward' | 'backward'

  // ── Computed ──────────────────────────────────────────────────────────

  // 文件类型：'ppt' | 'lesson_plan' | null
  const fileType = computed(() => {
    if (!uploadedFile.value) return null
    const ext = uploadedFile.value.name.split('.').pop().toLowerCase()
    if (['ppt', 'pptx'].includes(ext)) return 'ppt'
    return 'lesson_plan'
  })

  // 是否上传了 PPT
  const hasPPT = computed(() => fileType.value === 'ppt')

  // 上传文件不是开始的硬性条件——无文件也可以开始授课
  const canStart = computed(() => !isAnalyzing.value)

  const interviewQuestions = computed(
    () => analysisResult.value?.teacher_questions ?? DEFAULT_INTERVIEW_QUESTIONS
  )

  const totalQuestions = computed(() => interviewQuestions.value.length)

  const currentQuestion = computed(
    () => interviewQuestions.value[currentQuestionIndex.value] ?? null
  )

  const isInterviewComplete = computed(
    () => currentQuestionIndex.value >= totalQuestions.value
  )

  const interviewProgress = computed(() =>
    totalQuestions.value > 0
      ? Math.round((currentQuestionIndex.value / totalQuestions.value) * 100)
      : 0
  )

  // ── Actions ───────────────────────────────────────────────────────────
  async function uploadAndAnalyze(file) {
    uploadedFile.value = file
    isAnalyzing.value = true
    analysisResult.value = null

    try {
      const result = await analyzeLesson(file)
      analysisResult.value = result
      lessonId.value = `lesson-${Date.now()}`
    } finally {
      isAnalyzing.value = false
    }
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
    interviewAnswers.value = {}
    interviewDirection.value = 'forward'
  }

  function reset() {
    uploadedFile.value = null
    teacherContext.value = ''
    isAnalyzing.value = false
    analysisResult.value = null
    lessonId.value = null
    resetInterview()
  }

  return {
    uploadedFile,
    teacherContext,
    isAnalyzing,
    analysisResult,
    lessonId,
    fileType,
    hasPPT,
    currentQuestionIndex,
    interviewAnswers,
    interviewDirection,
    canStart,
    interviewQuestions,
    totalQuestions,
    currentQuestion,
    isInterviewComplete,
    interviewProgress,
    uploadAndAnalyze,
    answerAndNext,
    skipQuestion,
    goBack,
    resetInterview,
    reset,
  }
})
