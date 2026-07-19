const XFYUN_SIGN_PATH = '/backend-api/api/asr/xfyun/sign'
const SEND_INTERVAL_MS = 80

function toBase64(bytes) {
  let binary = ''
  const chunkSize = 0x8000
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize)
    binary += String.fromCharCode.apply(null, chunk)
  }
  return btoa(binary)
}

function downsampleTo16k(float32Data, sourceRate) {
  if (sourceRate === 16000) {
    const pcm = new Int16Array(float32Data.length)
    for (let i = 0; i < float32Data.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Data[i]))
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }
    return pcm
  }

  const ratio = sourceRate / 16000
  const newLength = Math.round(float32Data.length / ratio)
  const pcm = new Int16Array(newLength)

  let offsetResult = 0
  let offsetBuffer = 0
  while (offsetResult < pcm.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio)
    let accum = 0
    let count = 0
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < float32Data.length; i++) {
      accum += float32Data[i]
      count++
    }
    const sample = count > 0 ? accum / count : 0
    const clamped = Math.max(-1, Math.min(1, sample))
    pcm[offsetResult] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff
    offsetResult++
    offsetBuffer = nextOffsetBuffer
  }
  return pcm
}

async function fetchSignedWsUrl() {
  let res
  try {
    res = await fetch(XFYUN_SIGN_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    })
  } catch (err) {
    throw new Error(`无法连接到后端签名接口：${err?.message || err}`)
  }

  if (res.status === 401) {
    throw new Error('未登录或登录已过期，请重新登录后再试')
  }
  if (res.status === 503) {
    throw new Error('后端讯飞 ASR 配置缺失，请联系管理员配置 XFYUN_APP_ID/API_KEY/API_SECRET')
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`签名接口返回 ${res.status}：${text || '(无消息)'}`)
  }

  let json
  try {
    json = await res.json()
  } catch {
    throw new Error('签名接口响应解析失败')
  }
  if (!json?.ws_url || !json?.app_id) {
    throw new Error('签名接口响应缺少 ws_url 或 app_id')
  }
  return { wsUrl: json.ws_url, appId: json.app_id }
}

function extractTextFromResult(payload) {
  const result = payload?.data?.result
  if (!result || !Array.isArray(result.ws)) return ''
  return result.ws
    .map((item) => (item.cw || []).map((cw) => cw.w || '').join(''))
    .join('')
}

export class XfyunASRClient {
  constructor({ onText, onError, onClose } = {}) {
    this.onText = onText
    this.onError = onError
    this.onClose = onClose

    this.ws = null
    this.stream = null
    this.audioCtx = null
    this.processor = null
    this.source = null

    this.frameQueue = []
    this.sendTimer = null
    this.opened = false
    this.started = false
    this.appId = null
  }

  async start() {
    if (this.started) return
    this.started = true

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })

      this.audioCtx = new (window.AudioContext || window.webkitAudioContext)()
      if (this.audioCtx.state === 'suspended') {
        await this.audioCtx.resume()
      }
      this.source = this.audioCtx.createMediaStreamSource(this.stream)
      this.processor = this.audioCtx.createScriptProcessor(4096, 1, 1)

      this.processor.onaudioprocess = (event) => {
        if (!this.started) return
        const float32 = event.inputBuffer.getChannelData(0)
        const pcm16 = downsampleTo16k(float32, this.audioCtx.sampleRate)
        const bytes = new Uint8Array(pcm16.buffer)
        this.frameQueue.push(toBase64(bytes))
      }

      this.source.connect(this.processor)
      this.processor.connect(this.audioCtx.destination)

      const { wsUrl, appId } = await fetchSignedWsUrl()
      this.appId = appId
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.opened = true
        this.startSendLoop()
      }

      this.ws.onmessage = (evt) => {
        try {
          const payload = JSON.parse(evt.data)
          if (payload.code !== 0) {
            this.handleError(`讯飞识别失败(${payload.code})：${payload.message || '未知错误'}`)
            return
          }
          const result = payload?.data?.result
          const text = extractTextFromResult(payload)
          if (text) {
            const isFinal = Boolean(result?.ls) || Number(payload?.data?.status) === 2
            this.onText?.(text, {
              isFinal,
              status: Number(payload?.data?.status),
              raw: payload,
            })
          }
        } catch {
          this.handleError('讯飞响应解析失败')
        }
      }

      this.ws.onerror = () => {
        this.handleError('讯飞 WebSocket 连接异常')
      }

      this.ws.onclose = (evt) => {
        if (this.started && evt?.code !== 1000) {
          const code = evt?.code ?? 'unknown'
          const reason = evt?.reason || '无原因'
          this.onError?.(`讯飞连接关闭(code=${code})：${reason}`)
        }
        this.opened = false
        this.onClose?.(evt)
      }
    } catch (err) {
      this.started = false
      throw err
    }
  }

  startSendLoop() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return

    this.sendTimer = setInterval(() => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return
      const audio = this.frameQueue.shift()
      if (!audio || !this.opened) return

      const isFirst = this.ws._sentFirst !== true
      if (isFirst) {
        this.ws._sentFirst = true
        this.ws.send(JSON.stringify({
          common: { app_id: this.appId },
          business: {
            language: 'zh_cn',
            domain: 'iat',
            accent: 'mandarin',
            vinfo: 1,
            vad_eos: 3000,
          },
          data: {
            status: 0,
            format: 'audio/L16;rate=16000',
            encoding: 'raw',
            audio,
          },
        }))
      } else {
        this.ws.send(JSON.stringify({
          data: {
            status: 1,
            format: 'audio/L16;rate=16000',
            encoding: 'raw',
            audio,
          },
        }))
      }
    }, SEND_INTERVAL_MS)
  }

  stop() {
    this.started = false

    if (this.sendTimer) {
      clearInterval(this.sendTimer)
      this.sendTimer = null
    }

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify({
          data: {
            status: 2,
            format: 'audio/L16;rate=16000',
            encoding: 'raw',
            audio: '',
          },
        }))
      } catch {}
      setTimeout(() => this.ws?.close(), 120)
    } else {
      this.ws?.close()
    }

    this.processor?.disconnect()
    this.source?.disconnect()
    this.audioCtx?.close()
    this.stream?.getTracks().forEach((t) => t.stop())

    this.processor = null
    this.source = null
    this.audioCtx = null
    this.stream = null
    this.ws = null
    this.frameQueue = []
  }

  handleError(message) {
    this.onError?.(message)
    this.stop()
  }
}

export function isXfyunSupported() {
  return Boolean(
    window.isSecureContext &&
      window.WebSocket &&
      navigator.mediaDevices?.getUserMedia,
  )
}
