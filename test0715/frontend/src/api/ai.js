/**
 * AI 模块 API 服务
 * 对接杨云天的 FastAPI 服务（http://localhost:8001）
 * Vite proxy: /ai-api/* → http://localhost:8001/*
 */

const BASE = '/ai-api'
const BACKEND_BASE = '/backend-api'

export async function parseLessonFile(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/ai/parse_lesson`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(`AI 解析失败：${res.status}`)
  return res.json()
}

export async function parseLessonFiles(files) {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  const res = await fetch(`${BASE}/ai/parse_lessons`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(`AI 解析失败：${res.status}`)
  return res.json()
}

export async function supervisorDecide(payload) {
  const res = await fetch(`${BASE}/ai/supervisor/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Supervisor 决策失败：${res.status}`)
  return res.json()
}

export async function supervisorDecideV2(payload) {
  const res = await fetch(`${BASE}/ai/v2/inclass/supervisor/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Supervisor v2 决策失败：${res.status}`)
  return res.json()
}

export async function agentReply(payload) {
  const res = await fetch(`${BASE}/ai/agent/reply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Agent 回复失败：${res.status}`)
  return res.json()
}

export async function segmentEvalV2(payload) {
  const res = await fetch(`${BASE}/ai/v2/inclass/segment/eval`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Segment Eval v2 失败：${res.status}`)
  return res.json()
}

export async function initLessonBootstrap(payload) {
  const form = new FormData()
  form.append('grade', payload.grade)
  form.append('subject', payload.subject)
  form.append('class_level', payload.class_level)
  form.append('atmosphere', payload.atmosphere)
  form.append('custom_goal', payload.custom_goal || '')
  form.append('teacher_context', payload.teacher_context || '')
  if (payload.frontend_session_id) {
    form.append('frontend_session_id', payload.frontend_session_id)
  }
  if (payload.lesson_json) {
    form.append('lesson_json', JSON.stringify(payload.lesson_json))
  }
  if (payload.ppt_json) {
    form.append('ppt_json', JSON.stringify(payload.ppt_json))
  }
  if (payload.teaching_preferences_json) {
    form.append(
      'teaching_preferences_json',
      JSON.stringify(payload.teaching_preferences_json),
    )
  }
  if (payload.file) {
    form.append('file', payload.file)
  }

  const res = await fetch(`${BACKEND_BASE}/api/init_lesson`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(`课堂初始化失败：${res.status}`)
  return res.json()
}

export async function fetchLessonStatus(lessonId) {
  const res = await fetch(`${BACKEND_BASE}/api/lesson/${encodeURIComponent(lessonId)}/status`)
  if (!res.ok) throw new Error(`获取课程状态失败：${res.status}`)
  return res.json()
}

export async function postInclassUtterance(payload) {
  const res = await fetch(`${BACKEND_BASE}/api/inclass/utterance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`后端课堂入口失败：${res.status}`)
  return res.json()
}

export async function fetchStudentState(studentId) {
  const res = await fetch(
    `${BACKEND_BASE}/api/inclass/student-state/${encodeURIComponent(studentId)}`,
  )
  if (!res.ok) throw new Error(`获取学生状态失败：${res.status}`)
  return res.json()
}

export async function postInclassSegment(payload) {
  const res = await fetch(`${BACKEND_BASE}/api/inclass/segment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`后端片段入库失败：${res.status}`)
  return res.json()
}

export async function fetchReport(sessionId) {
  const res = await fetch(`${BACKEND_BASE}/api/report/${encodeURIComponent(sessionId)}`)
  if (!res.ok) throw new Error(`获取报告失败：${res.status}`)
  return res.json()
}
