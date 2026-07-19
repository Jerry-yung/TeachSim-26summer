/**
 * MiniMax T2A（后端短连接 WebSocket 代理 → MP3 二进制流）
 *
 * 音色仅按 student_id（小明/小红/小王/小乐）选择，与 agent_type 无关。
 */

const BACKEND_BASE = '/backend-api'

/** 与 backend/app/services/minimax_t2a.py 保持一致 */
export const STUDENT_ID_VOICE = {
  student_xm: 'male-qn-qingse',       // 小明 · 男
  student_xw: 'female-shaonv',        // 小红 · 女
  student_xw2: 'male-qn-jingying',     // 小王 · 男
  student_xl: 'female-chengshu',       // 小乐 · 女
}

export const DEFAULT_VOICE = 'male-qn-qingse'

let activeAudio = null
let activeObjectUrl = ''

function cleanupActivePlayback() {
  if (activeAudio) {
    try {
      activeAudio.pause()
      activeAudio.src = ''
    } catch {
      /* ignore */
    }
    activeAudio = null
  }
  if (activeObjectUrl) {
    URL.revokeObjectURL(activeObjectUrl)
    activeObjectUrl = ''
  }
}

export function stopMinimaxPlayback() {
  cleanupActivePlayback()
}

/**
 * @param {string} text
 * @param {{ studentId?: string }} [options]
 * @returns {Promise<boolean|null>} true=MiniMax 播放成功；null=降级浏览器 TTS
 */
export async function minimaxSpeak(text, options = {}) {
  const trimmed = String(text || '').trim()
  if (!trimmed) return null

  cleanupActivePlayback()

  try {
    const res = await fetch(`${BACKEND_BASE}/api/tts/minimax/synthesize`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: trimmed,
        student_id: options.studentId || null,
      }),
    })

    if (!res.ok) {
      return null
    }

    const blob = await res.blob()
    if (!blob.size) {
      return null
    }

    activeObjectUrl = URL.createObjectURL(blob)
    const audio = new Audio(activeObjectUrl)
    activeAudio = audio

    await new Promise((resolve, reject) => {
      const onDone = () => {
        audio.removeEventListener('ended', onDone)
        audio.removeEventListener('error', onError)
        resolve()
      }
      const onError = () => {
        audio.removeEventListener('ended', onDone)
        audio.removeEventListener('error', onError)
        reject(new Error('MiniMax audio playback failed'))
      }
      audio.addEventListener('ended', onDone)
      audio.addEventListener('error', onError)
      void audio.play().catch(onError)
    })

    cleanupActivePlayback()
    return true
  } catch {
    cleanupActivePlayback()
    return null
  }
}
