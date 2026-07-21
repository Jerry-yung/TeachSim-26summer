const XFYUN_SIGN_PATH = '/backend-api/api/asr/xfyun/sign'
const SEND_INTERVAL_MS = 80
/** 句末静音判停（毫秒）；过大则说完后长时间无 final */
const VAD_EOS_MS = 3000
/** 新会话建立时保留最近帧数（约 0.5s），避免轮转空窗内刚开口的话被整段丢弃 */
const KEEP_FRAMES_ON_ROTATE = 8
/** 轮转/断连期间麦克风仍采集，限制积压帧，避免恢复后长时间回放旧音频 */
const MAX_FRAME_QUEUE = 48
/** 讯飞：会话已结束仍发中间帧等 → 静默换新连接，不视为致命错误 */
const RECOVERABLE_CODES = new Set([10165])

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

function isRecoverableCode(code) {
  const n = Number(code)
  return RECOVERABLE_CODES.has(n)
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
    this.sentFirst = false
    /** 当前 WS 可接收 status=1 音频 */
    this.sessionReady = false
    this.rotating = false
    this._closeForRotate = false
    this._sendLoopStarted = false
    this._rotatePromise = null
  }

  async start() {
    if (this.started) return
    this.started = true

    try {
      await this._ensureMicrophonePipeline()
      await this.rotateSession()
    } catch (err) {
      this.started = false
      throw err
    }
  }

  async _ensureMicrophonePipeline() {
    if (this.stream) return

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
      if (this.frameQueue.length > MAX_FRAME_QUEUE) {
        this.frameQueue.splice(0, this.frameQueue.length - MAX_FRAME_QUEUE)
      }
    }

    this.source.connect(this.processor)
    // 仅用于驱动 ScriptProcessor，避免接到扬声器产生回声
    const silentGain = this.audioCtx.createGain()
    silentGain.gain.value = 0
    this.processor.connect(silentGain)
    silentGain.connect(this.audioCtx.destination)
  }

  /**
   * 方案 1a：句末或 10165 后静默换新 WebSocket，麦克风与发送循环不中断。
   */
  async rotateSession() {
    if (!this.started) return
    if (this._rotatePromise) return this._rotatePromise

    this._rotatePromise = this._doRotateSession()
    try {
      await this._rotatePromise
    } finally {
      this._rotatePromise = null
    }
  }

  _discardBufferedAudio() {
    this.frameQueue = []
  }

  async _doRotateSession() {
    if (!this.started) return
    if (this.rotating) return

    this.rotating = true
    this.sessionReady = false
    this.sentFirst = false
    // 断连期间采集的静音/环境声不应送入新会话
    this._discardBufferedAudio()

    // 与关闭旧连接并行取签名，缩短句末空窗
    const signPromise = fetchSignedWsUrl()

    const oldWs = this.ws
    if (oldWs) {
      this._closeForRotate = true
      oldWs.onmessage = null
      oldWs.onerror = null
      oldWs.onclose = null
      try {
        if (oldWs.readyState === WebSocket.OPEN) {
          oldWs.close(1000, 'rotate')
        }
      } catch {
        /* ignore */
      }
      this.ws = null
      this.opened = false
    }

    try {
      const { wsUrl, appId } = await signPromise
      this.appId = appId
      const ws = new WebSocket(wsUrl)
      this.ws = ws

      ws.onopen = () => {
        if (!this.started || this.ws !== ws) return
        this.opened = true
        // 丢弃轮转前的积压静音，保留刚采集的少量实时帧
        if (this.frameQueue.length > KEEP_FRAMES_ON_ROTATE) {
          this.frameQueue = this.frameQueue.slice(-KEEP_FRAMES_ON_ROTATE)
        }
        this.sessionReady = true
        this.rotating = false
        this._closeForRotate = false
        if (!this._sendLoopStarted) {
          this._sendLoopStarted = true
          this.startSendLoop()
        }
      }

      ws.onmessage = (evt) => this._handleWsMessage(evt, ws)

      ws.onerror = () => {
        if (!this.started || this.ws !== ws || this._closeForRotate) return
        void this._handleConnectionLoss('讯飞 WebSocket 连接异常')
      }

      ws.onclose = (evt) => {
        if (this.ws !== ws) return
        this.opened = false
        this.sessionReady = false
        if (this._closeForRotate || !this.started) {
          this._closeForRotate = false
          return
        }
        void this._handleConnectionLoss(
          `讯飞连接关闭(code=${evt?.code ?? 'unknown'})：${evt?.reason || '无原因'}`,
        )
      }

      await new Promise((resolve, reject) => {
        const t = setTimeout(() => reject(new Error('讯飞 WebSocket 连接超时')), 8000)
        const prevOnOpen = ws.onopen
        ws.onopen = (ev) => {
          clearTimeout(t)
          prevOnOpen?.call(ws, ev)
          resolve()
        }
        const prevOnClose = ws.onclose
        ws.onclose = (ev) => {
          if (ws.readyState === WebSocket.CLOSED && !this.sessionReady) {
            clearTimeout(t)
            reject(new Error('讯飞 WebSocket 在建立前关闭'))
          }
          prevOnClose?.call(ws, ev)
        }
      })
    } catch (err) {
      this.rotating = false
      this._closeForRotate = false
      throw err
    }
  }

  _handleWsMessage(evt, ws) {
    if (!this.started || this.ws !== ws) return
    try {
      const payload = JSON.parse(evt.data)
      const code = Number(payload.code)

      if (code !== 0) {
        if (isRecoverableCode(code)) {
          void this.rotateSession()
          return
        }
        this.handleFatalError(
          `讯飞识别失败(${code})：${payload.message || '未知错误'}`,
        )
        return
      }

      const result = payload?.data?.result
      const text = extractTextFromResult(payload)
      const status = Number(payload?.data?.status)
      const isFinal = Boolean(result?.ls) || status === 2

      if (text) {
        this.onText?.(text, {
          isFinal,
          status,
          raw: payload,
        })
      }

      if (isFinal) {
        // 延迟一拍再轮转，确保 final 回调已写入 UI
        setTimeout(() => {
          if (this.started) void this.rotateSession()
        }, 0)
      }
    } catch {
      this.handleFatalError('讯飞响应解析失败')
    }
  }

  async _handleConnectionLoss(reason) {
    if (!this.started || this.rotating) return
    try {
      await this.rotateSession()
    } catch {
      this.handleFatalError(reason)
    }
  }

  startSendLoop() {
    if (this.sendTimer) return

    this.sendTimer = setInterval(() => {
      if (!this.started) return
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return
      if (!this.sessionReady || this.rotating) return

      const audio = this.frameQueue.shift()
      if (!audio) return

      if (!this.sentFirst) {
        this.sentFirst = true
        this.ws.send(JSON.stringify({
          common: { app_id: this.appId },
          business: {
            language: 'zh_cn',
            domain: 'iat',
            accent: 'mandarin',
            vinfo: 1,
            vad_eos: VAD_EOS_MS,
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
    this.sessionReady = false
    this.rotating = false
    this._closeForRotate = true

    if (this.sendTimer) {
      clearInterval(this.sendTimer)
      this.sendTimer = null
    }
    this._sendLoopStarted = false

    if (this.ws) {
      const ws = this.ws
      ws.onmessage = null
      ws.onerror = null
      ws.onclose = null
      try {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            data: {
              status: 2,
              format: 'audio/L16;rate=16000',
              encoding: 'raw',
              audio: '',
            },
          }))
        }
      } catch {
        /* ignore */
      }
      setTimeout(() => {
        try {
          ws.close(1000, 'stop')
        } catch {
          /* ignore */
        }
      }, 120)
      this.ws = null
    }

    this.processor?.disconnect()
    this.source?.disconnect()
    this.audioCtx?.close()
    this.stream?.getTracks().forEach((t) => t.stop())

    this.processor = null
    this.source = null
    this.audioCtx = null
    this.stream = null
    this.opened = false
    this.sentFirst = false
    this.frameQueue = []
    this._closeForRotate = false

    this.onClose?.({ code: 1000, reason: 'stop' })
  }

  /** 致命错误后软恢复：保留麦克风时仅轮转 WS，否则完整 start */
  async resumeAfterFailure() {
    if (this.stream) {
      this.started = true
      this._closeForRotate = false
      await this.rotateSession()
      return
    }
    await this.start()
  }

  handleFatalError(message) {
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
