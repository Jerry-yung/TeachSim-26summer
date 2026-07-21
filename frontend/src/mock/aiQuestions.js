/**
 * 模拟后端接口：POST /api/init_lesson → 轮询 GET /api/lesson/{id}/status
 *
 * 真实架构分工：
 *   前端（你）  → 提供上传通道，轮询状态，展示问卷
 *   后端（王宏伟）→ 接收文件，存储，调用 AI 模块
 *   AI（杨云天） → RAG 解析文件内容，提取大纲，生成 teacher_questions
 *
 * teacher_questions 由后端 AI 根据文件内容动态生成，
 * 前端只负责渲染，不参与生成逻辑。
 * 替换真实接口时，修改 lessonStore.js 中 uploadAndAnalyze 的实现即可。
 */

/**
 * 面试式逐题问卷（由 AI 根据教案内容生成，此处为 Mock）
 * 每道题由 AI 决定是否提问——若老师在"教学背景描述"中已提及相关信息，
 * 真实版后端可将该题标记为 skip=true，前端跳过展示。
 */
export const DEFAULT_INTERVIEW_QUESTIONS = [
  {
    id: 'duration',
    type: 'radio',
    label: '预计本次上课时长？',
    emoji: '⏱️',
    required: true,
    skippable: false,
    options: ['30 分钟', '40 分钟', '45 分钟', '50 分钟', '60 分钟'],
  },
  {
    id: 'grade',
    type: 'radio',
    label: '您的学生是哪个年级？',
    emoji: '🎓',
    required: true,
    skippable: false,
    options: ['初一', '初二', '初三', '高一', '高二', '高三'],
  },
  {
    id: 'class_level',
    type: 'radio',
    label: '您希望授课的班级类型是？',
    emoji: '🏫',
    required: true,
    skippable: false,
    options: ['重点班', '普通班', '平行班'],
  },
  {
    id: 'student_level',
    type: 'radio',
    label: '您如何判断这节课的学生整体基础？',
    emoji: '📊',
    required: false,
    skippable: true,
    options: [
      '扎实：大多数同学有充分的前置基础',
      '中等：部分同学有基础，部分较薄弱',
      '较弱：从零开始，需要基础性引导',
    ],
  },
  {
    id: 'lesson_goal',
    type: 'radio',
    label: '本节课您希望学生主要达成哪类目标？',
    emoji: '🎯',
    allow_multiple: true,
    required: false,
    skippable: true,
    options: [
      '知识理解与记忆',
      '技能掌握与方法运用',
      '思维拓展与探究讨论',
      '情感体验与价值建构',
    ],
  },
  {
    id: 'practice_focus',
    type: 'radio',
    label: '本次课您最想在哪个方面有所突破？',
    hint: '课后报告将对此进行重点定向分析',
    emoji: '💡',
    allow_multiple: true,
    required: false,
    skippable: true,
    options: [
      '课堂节奏把控',
      '知识点衔接流畅度',
      '提问质量与互动引导',
      '语言表达与亲和力',
      '时间分配合理性',
    ],
  },
  {
    id: 'discipline_simulation_level',
    type: 'radio',
    label: '课堂纪律事件模拟强度（睡觉/交头接耳）',
    emoji: '🚨',
    required: false,
    skippable: true,
    options: ['高频（重点训练）', '中频', '低频', '关闭（不触发）'],
  },
  {
    id: 'atmosphere',
    type: 'radio',
    label: '您期望的课堂氛围是？',
    emoji: '🌡️',
    required: true,
    skippable: false,
    options: ['活跃互动型', '均衡参与型', '沉浸讲解型'],
  },
]

/**
 * 模拟调用后端接口
 * @param {File} file - 上传的文件对象
 * @returns {Promise<Object>} 模拟的后端分析响应
 */
export function analyzeLesson(file) {
  return new Promise((resolve) => {
    setTimeout(() => {
      const topicName = file.name.replace(/\.[^.]+$/, '')
      resolve({
        lesson_topic: `《${topicName}》`,
        subject: '由 AI 识别',
        subject_icon: '📄',
        knowledge_points_preview: [
          '（AI 提取的知识点大纲将在此展示）',
          '（由杨云天的 AI 模块生成，前端只负责渲染）',
        ],
        // 面试式问卷，AI 根据文件内容生成
        // 真实版：每题可含 skip=true 字段（根据老师预填的描述推断）
        teacher_questions: DEFAULT_INTERVIEW_QUESTIONS,
      })
    }, 2000)
  })
}
