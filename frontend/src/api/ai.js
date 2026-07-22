const AI_BASE = '/ai-api'
const BACKEND_BASE = '/backend-api'
const historyCache = new Map()

async function parseJsonResponse(res) {
  if (res.status === 204) return null
  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }
  if (!res.ok) {
    const message = data?.message || `Request failed: ${res.status}`
    throw new Error(message)
  }
  return data
}

async function backendFetch(path, init = {}) {
  const res = await fetch(`${BACKEND_BASE}${path}`, {
    credentials: 'include',
    ...init,
  })
  return parseJsonResponse(res)
}

function historyCacheKey(params = {}) {
  const limit = Number.isFinite(params.limit) ? params.limit : 30
  const offset = Number.isFinite(params.offset) ? params.offset : 0
  const topic = String(params.topic || '').trim()
  const startDate = String(params.start_date || '').trim()
  const endDate = String(params.end_date || '').trim()
  return `cookie-auth::${limit}::${offset}::${topic}::${startDate}::${endDate}`
}

export function clearHistoryCache() {
  historyCache.clear()
}

export async function parseLessonFile(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${AI_BASE}/ai/parse_lesson`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(`AI 解析失败: ${res.status}`)
  return res.json()
}

export async function parseLessonFiles(files) {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  const res = await fetch(`${AI_BASE}/ai/parse_lessons`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(`AI 解析失败: ${res.status}`)
  return res.json()
}

export async function supervisorDecide(payload) {
  const res = await fetch(`${AI_BASE}/ai/supervisor/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Supervisor 决策失败: ${res.status}`)
  return res.json()
}

export async function supervisorDecideV2(payload) {
  const res = await fetch(`${AI_BASE}/ai/v2/inclass/supervisor/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Supervisor v2 决策失败: ${res.status}`)
  return res.json()
}

export async function agentReply(payload) {
  const res = await fetch(`${AI_BASE}/ai/agent/reply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Agent 回复失败: ${res.status}`)
  return res.json()
}

export async function segmentEvalV2(payload) {
  const res = await fetch(`${AI_BASE}/ai/v2/inclass/segment/eval`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Segment Eval v2 失败: ${res.status}`)
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
  return backendFetch('/api/init_lesson', {
    method: 'POST',
    body: form,
  })
}

export function fetchLessonStatus(lessonId) {
  return backendFetch(`/api/lesson/${encodeURIComponent(lessonId)}/status`)
}

export async function fetchLessonPptPreview(lessonId) {
  const data = await backendFetch(`/api/lesson/${encodeURIComponent(lessonId)}/ppt-preview`)
  if (data?.preview_path) {
    data.preview_url = `${BACKEND_BASE}${data.preview_path}`
  } else {
    data.preview_url = ''
  }
  return data
}

/** 携带鉴权拉取课件 PDF 字节（供 PDF.js 使用，避免 cookie 鉴权） */
export async function fetchPptPreviewPdfBytes(previewUrl) {
  const raw = String(previewUrl || '').trim()
  if (!raw) throw new Error('preview_url 为空')
  if (raw.startsWith('blob:')) {
    const res = await fetch(raw)
    if (!res.ok) throw new Error(`blob PDF 读取失败：${res.status}`)
    return new Uint8Array(await res.arrayBuffer())
  }
  const u = new URL(raw, typeof window !== 'undefined' ? window.location.origin : undefined)
  const pathWithQuery = `${u.pathname}${u.search || ''}`
  const apiPath = pathWithQuery.startsWith('/backend-api')
    ? pathWithQuery.slice('/backend-api'.length)
    : pathWithQuery
  const res = await fetch(`${BACKEND_BASE}${apiPath}`, { credentials: 'include' })
  if (!res.ok) throw new Error(`课件 PDF 下载失败：${res.status}`)
  return new Uint8Array(await res.arrayBuffer())
}

export function restartClassroomSession(sessionId) {
  return backendFetch(`/api/session/${encodeURIComponent(sessionId)}/restart`, {
    method: 'POST',
  })
}

export function postInclassUtterance(payload) {
  return backendFetch('/api/inclass/utterance', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function fetchStudentState(studentId, sessionId = '') {
  const suffix = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
  return backendFetch(`/api/inclass/student-state/${encodeURIComponent(studentId)}${suffix}`)
}

export function postInclassSegment(payload) {
  return backendFetch('/api/inclass/segment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function postStudentReply(payload) {
  return backendFetch('/api/inclass/student-reply', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function fetchReport(sessionId, options = {}) {
  const q = new URLSearchParams()
  if (options?.force === true) q.set('force', 'true')
  if (options?.waitVisual !== false) q.set('wait_visual', 'true')
  const suffix = q.toString() ? `?${q.toString()}` : ''
  return backendFetch(`/api/report/${encodeURIComponent(sessionId)}${suffix}`)
}

export function fetchRecent5Comparison(sessionId) {
  return backendFetch(`/api/report/${encodeURIComponent(sessionId)}/recent5-comparison`)
}

export async function fetchHistorySessions(params = {}) {
  const limit = Number.isFinite(params.limit) ? params.limit : 30
  const offset = Number.isFinite(params.offset) ? params.offset : 0
  const topic = String(params.topic || '').trim()
  const startDate = String(params.start_date || '').trim()
  const endDate = String(params.end_date || '').trim()
  const cacheKey = historyCacheKey({ limit, offset, topic, start_date: startDate, end_date: endDate })
  if (params.use_cache === true && historyCache.has(cacheKey)) {
    return historyCache.get(cacheKey)
  }

  const q = new URLSearchParams()
  q.set('limit', String(limit))
  q.set('offset', String(offset))
  if (topic) q.set('topic', topic)
  if (startDate) q.set('start_date', startDate)
  if (endDate) q.set('end_date', endDate)

  const data = await backendFetch(`/api/history/sessions?${q.toString()}`)
  historyCache.set(cacheKey, data)
  return data
}

export function getCachedHistorySessions(params = {}) {
  return historyCache.get(historyCacheKey(params)) || null
}

export async function primeHistorySessionsCache(params = {}) {
  try {
    await fetchHistorySessions({ ...params, use_cache: false })
  } catch {
    // warm-up failure should not block login flow
  }
}

export function fetchHistorySession(sessionId) {
  return backendFetch(`/api/history/sessions/${encodeURIComponent(sessionId)}`)
}

export function fetchHistorySessionDates(params = {}) {
  const topic = String(params.topic || '').trim()
  const q = new URLSearchParams()
  if (topic) q.set('topic', topic)
  const suffix = q.toString()
  return backendFetch(`/api/history/session-dates${suffix ? `?${suffix}` : ''}`)
}

export function fetchLatestPreset() {
  return backendFetch('/api/history/latest-preset')
}

export function fetchAbilityProfile() {
  return backendFetch('/api/history/ability-profile')
}

export async function deleteHistorySession(sessionId) {
  const data = await backendFetch(`/api/history/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  })
  clearHistoryCache()
  return data
}
