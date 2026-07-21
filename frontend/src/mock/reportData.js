/**
 * Mock 课后报告数据
 * 真实版本：GET /api/report/{session_id}
 *
 * 设计原则：报告是给老师看自己表现的展示汇报，不用分数量化课堂。
 * 维度内部保留归一化值（仅用于雷达图渲染形状），不对外展示。
 */

// 内部映射：将内部值转为定性等级
function toLevel(val) {
  if (val >= 85) return { label: '优秀', cls: 'green' }
  if (val >= 70) return { label: '良好', cls: 'blue' }
  if (val >= 60) return { label: '待提升', cls: 'amber' }
  return { label: '需关注', cls: 'red' }
}

const _scores = {
  content_accuracy: 85,
  syllabus_alignment: 90,
  interaction_quality: 70,
  pacing: 72,
  language_appropriateness: 80,
}

export const mockReport = {
  session_id: 'mock-session-001',
  lesson_topic: '《六国论》',
  subject: '高中语文 · 古文',
  class_info: '高二 · 重点班',
  created_at: '2026-07-21 14:32',
  duration_min: 42,

  // 定性总体评价（替代综合分数）
  overall_level: '整体良好',
  overall_desc: '知识讲授扎实，互动节奏有提升空间',

  // 维度定性表现（雷达图用内部值渲染形状，展示用 level）
  dimensions: Object.entries(_scores).map(([key, val]) => ({
    key,
    label: {
      content_accuracy: '内容准确',
      syllabus_alignment: '教案贴合',
      interaction_quality: '互动质量',
      pacing: '课堂节奏',
      language_appropriateness: '语言表达',
    }[key],
    _val: val,         // 仅用于雷达图渲染，不在 UI 上显示
    level: toLevel(val),
  })),

  hard_stats: {
    total_duration_min: 42,
    talk_duration_min: 36,
    total_words: 6820,
    avg_speed_wpm: 162,
    avg_wait_time_sec: 1.2,
    filler_words: [
      { word: '对不对', count: 12 },
      { word: '就是', count: 8 },
      { word: '呃', count: 5 },
      { word: '然后', count: 14 },
    ],
  },

  time_distribution: [
    { segment: '课堂导入', duration: 8, color: '#6366F1' },
    { segment: '新知讲授', duration: 20, color: '#2563EB' },
    { segment: '互动问答', duration: 10, color: '#10B981' },
    { segment: '总结巩固', duration: 4, color: '#F59E0B' },
  ],

  question_types: [
    { type: '封闭式', count: 6, color: '#E5E7EB' },
    { type: '引导式', count: 7, color: '#BFDBFE' },
    { type: '开放式', count: 2, color: '#2563EB' },
  ],

  // 练习目标反馈——只有定性评级，不出现分数
  custom_goal_feedback: {
    goal: '课堂节奏与环节衔接',
    level: { label: '待提升', cls: 'amber' },
    feedback:
      '本节课各环节的衔接存在一定生硬感，从新授讲解到互动提问的过渡较为突兀，学生需要时间适应节奏转变。建议在结束新知讲解时，用一句自然过渡语引入互动环节，例如："同学们，我们刚才分析了六国灭亡的外部原因，那从六国自身来看，又存在哪些问题呢？"',
  },

  improvement_suggestions:
    '本节课教案贴合度高，知识点讲授准确，整体表现良好。主要改进方向：\n\n① **互动质量有待提升**：全程仅有 15 个学生互动片段，封闭式提问占比偏高（40%），建议增加 2-3 个开放性讨论题，引导学生主动思考。\n\n② **课堂节奏偏快**：部分核心知识点（如"赂秦"论点的辩证分析）停留时间不足 2 分钟，学生可能尚未充分消化。建议在重点处留白等待，提问等待时间均值仅 1.2 秒，低于推荐的 3 秒。\n\n③ **口头禅控制**："然后"出现 14 次、"对不对"12 次，建议有意识地替换为更有变化的过渡语。',

  is_improved: true,
  history_comparison:
    '对比上节课（《阿房宫赋》），您的**互动质量有了明显改善**，在主动引导学生思考方面取得了显著进步，课堂氛围更加活跃。课堂节奏的把控是本次继续努力的方向，建议重点练习重难点处的节奏留白。',

  highlight_events: [
    { time: '08:32', type: 'good', text: '知识点引入自然，学生参与度高' },
    { time: '19:45', type: 'warning', text: '语速偏快，核心词汇"弊在赂秦"讲解不足 30 秒' },
    { time: '27:10', type: 'good', text: '追问"如果不赂秦结果会不同吗？"引发课堂热烈讨论' },
    { time: '35:22', type: 'warning', text: '环节衔接生硬，从讲授直接跳入总结，缺少过渡' },
  ],
}
