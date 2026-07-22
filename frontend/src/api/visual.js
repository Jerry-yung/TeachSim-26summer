/**
 * 课中视觉观察 API 客户端
 *
 * 上传单个 15s 窗口的缩略图/clip + 元数据，后端异步触发 VLM 分析。
 * 用法：
 *   import { postVisualObservation } from '@/api/visual'
 *   await postVisualObservation({ sessionId, observationId, ... })
 */

// 与 ai.js 一致：本地 Vite 代理 /backend-api → 8010
const BACKEND_BASE = import.meta.env.VITE_API_BASE_URL || '/backend-api'
const BASE = `${BACKEND_BASE}/api`

/**
 * 上传一个视觉观察窗口
 *
 * @param {object} opts
 * @param {string}   opts.sessionId
 * @param {string}   opts.observationId     唯一 ID，格式建议 `${sessionId}_w${windowIndex}`
 * @param {string}   [opts.segmentId]       当前所属语音片段 ID
 * @param {number}   [opts.windowStartSec]  窗口起始秒（课程绝对时间）
 * @param {number}   [opts.windowEndSec]    窗口结束秒
 * @param {number}   [opts.slideNo]         当前 PPT 页码
 * @param {boolean}  [opts.precheckPassed]  MediaPipe 预检是否通过
 * @param {string[]} [opts.framesB64]       1-3 张 JPEG base64（无前缀）
 * @param {Blob}     [opts.clip]            2-3s WebM Blob
 * @param {Blob}     [opts.thumbnail]       缩略图 JPEG Blob
 * @param {Array}    [opts.chatHistory]     最近 20 条师生对话（可选，后端有兜底）
 * @returns {Promise<{observation_id:string, status:string}>}
 */
export async function postVisualObservation({
  sessionId,
  observationId,
  segmentId,
  windowStartSec = 0,
  windowEndSec = 15,
  slideNo,
  precheckPassed = true,
  framesB64 = [],
  clip,
  thumbnail,
  chatHistory = [],
}) {
  const fd = new FormData()
  fd.append('session_id', sessionId)
  fd.append('observation_id', observationId)
  if (segmentId) fd.append('segment_id', segmentId)
  fd.append('window_start_sec', String(windowStartSec))
  fd.append('window_end_sec', String(windowEndSec))
  if (slideNo != null) fd.append('slide_no', String(slideNo))
  fd.append('precheck_passed', precheckPassed ? 'true' : 'false')
  fd.append('chat_history_json', JSON.stringify(chatHistory))
  fd.append('frames_b64_json', JSON.stringify(framesB64))

  if (clip instanceof Blob) {
    fd.append('clip', clip, `${observationId}.webm`)
  }
  if (thumbnail instanceof Blob) {
    fd.append('thumbnail', thumbnail, `${observationId}_thumb.jpg`)
  }

  const resp = await fetch(`${BASE}/inclass/visual-observation`, {
    method: 'POST',
    credentials: 'include',
    body: fd,
  })

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    const msg = err?.message || err?.detail || `HTTP ${resp.status}`
    throw new Error(`postVisualObservation failed: ${msg}`)
  }
  return resp.json()
}

/**
 * 获取 visual clip 播放 URL（鉴权后流式）
 * @param {string} sessionId
 * @param {string} observationId
 * @returns {string} 请求 URL（需携带 Cookie）
 */
export function getVisualClipUrl(sessionId, observationId) {
  return `${BASE}/report/${sessionId}/visual-clip/${observationId}`
}

/**
 * 获取 visual 缩略图 URL
 */
export function getVisualThumbUrl(sessionId, observationId) {
  return `${BASE}/report/${sessionId}/visual-thumb/${observationId}`
}
