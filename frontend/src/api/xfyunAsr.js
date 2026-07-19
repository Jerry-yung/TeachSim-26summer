const XFYUN_HOST = 'iat-api.xfyun.cn'
const XFYUN_PATH = '/v2/iat'
const XFYUN_URL = `wss://${XFYUN_HOST}${XFYUN_PATH}`

const APP_ID = import.meta.env.VITE_XFYUN_APP_ID
const API_KEY = import.meta.env.VITE_XFYUN_API_KEY
const API_SECRET = import.meta.env.VITE_XFYUN_API_SECRET

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

async function buildAuthUrl() {
  if (!APP_ID || !API_KEY || !API_SECRET) {
    throw new Error('讯飞 ASR Key 未配置，请在 .env 中填写 VITE_XFYUN_APP_ID / API_KEY / API_SECRET')
  }

  const date = new Date().toUTCString()
  const signatureOrigin = `host: ${XFYUN_HOST}\ndate: ${date}\nGET ${XFYUN_PATH} HTTP/1.1`

  const enc = new TextEncoder()
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    enc.encode(API_SECRET),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  )
  const signBuffer = await crypto.subtle.sign('HMAC', cryptoKey, enc.encode(signatureOrigin))
  const signature = toBase64(new Uint8Array(signBuffer))

  const authorizationOrigin = `api_key="${API_KEY}", algorithm="hmac-sha256", headers="host date request-line", signature="${signature}"`
  const authorization = btoa(authorizationOrigin)

  return `${XFYUN_URL}?authorization=${encodeURIComponent(authorization)}&date=${encodeURIComponent(date)}&host=${XFYUN_HOST}`
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

      const wsUrl = await buildAuthUrl()
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
          const text = extractTextFromResult(payload)
          if (text) this.onText?.(text)
        } catch {
          this.handleError('讯飞响应解析失败')
        }
      }

      this.ws.onerror = () => {
        this.handleError('讯飞 WebSocket 连接异常（onerror）')
      }

      this.ws.onclose = (evt) => {
        // 非主动关闭时，补充关闭码信息，便于定位鉴权/网络问题
        if (this.started && evt?.code !== 1000) {
          const code = evt?.code ?? 'unknown'
          const reason = evt?.reason || '无原因'
          this.onError?.(`讯飞连接关闭（code=${code}）：${reason}`)
        }
        this.opened = false
        this.onClose?.()
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
      if (!audio) return

      if (!this.opened) return

      const isFirst = this.ws._sentFirst !== true
      if (isFirst) {
        this.ws._sentFirst = true
        this.ws.send(JSON.stringify({
          common: { app_id: APP_ID },
          business: {
            language: 'zh_cn',
            domain: 'iat',
            accent: 'mandarin',
            vinfo: 1,
            vad_eos: 5000,
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
    }, 40)
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
      } catch {
        // ignore
      }
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
      window.crypto?.subtle &&
      navigator.mediaDevices?.getUserMedia,
  )
}
