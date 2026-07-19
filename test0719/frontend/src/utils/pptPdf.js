/**
 * 课堂课件 PDF：PDF.js 加载 + 按 pptPage 渲染到 canvas（替代 iframe / #page=）
 */
import * as pdfjsLib from 'pdfjs-dist'
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { fetchPptPreviewPdfBytes } from '@/api/ai'

let workerReady = false

function ensureWorker() {
  if (workerReady) return
  pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker
  workerReady = true
}

/** 去掉 cache-bust 参数，便于课前预热与课堂页共用缓存 */
export function normalizePdfCacheKey(url) {
  const s = String(url || '').trim()
  if (!s) return ''
  if (s.startsWith('blob:')) return s
  try {
    const u = new URL(s, typeof window !== 'undefined' ? window.location.origin : undefined)
    u.searchParams.delete('t')
    return u.toString()
  } catch {
    return s
  }
}

let cachedDoc = null
let cachedKey = null

export function invalidatePptPdfCache() {
  if (!cachedDoc) {
    cachedKey = null
    return
  }
  const d = cachedDoc
  cachedDoc = null
  cachedKey = null
  d.destroy().catch(() => {})
}

/**
 * @param {string} url
 * @returns {Promise<import('pdfjs-dist').PDFDocumentProxy>}
 */
export async function loadPptPdfDocument(url) {
  ensureWorker()
  const key = normalizePdfCacheKey(url)
  if (cachedDoc && cachedKey === key) return cachedDoc
  invalidatePptPdfCache()

  const raw = String(url || '').trim()
  if (!raw) throw new Error('缺少 PDF 地址')

  let loadingTask
  if (raw.startsWith('blob:')) {
    loadingTask = pdfjsLib.getDocument({ url: raw })
  } else {
    const data = await fetchPptPreviewPdfBytes(raw)
    loadingTask = pdfjsLib.getDocument({ data })
  }

  const doc = await loadingTask.promise
  cachedDoc = doc
  cachedKey = key
  return doc
}

export async function warmupPptPdfFromUrl(previewUrl) {
  const u = String(previewUrl || '').trim()
  if (!u) return null
  return loadPptPdfDocument(u)
}

/**
 * @param {import('pdfjs-dist').PDFDocumentProxy} doc
 * @param {number} pageNum 1-based
 * @param {HTMLCanvasElement} canvas
 * @param {number} maxCssWidth 容器 CSS 像素宽度
 * @param {number} maxCssHeight 容器 CSS 像素高度（与宽度一起决定「整页可见」缩放）
 */
export async function renderPptPdfPage(doc, pageNum, canvas, maxCssWidth, maxCssHeight) {
  const total = doc.numPages || 0
  const n = Math.min(Math.max(1, Math.floor(Number(pageNum) || 1)), Math.max(1, total))
  const page = await doc.getPage(n)
  const base = page.getViewport({ scale: 1 })
  const mw = Math.max(80, Number(maxCssWidth) || 640)
  const mh = Math.max(60, Number(maxCssHeight) || 400)
  const scaleW = mw / base.width
  const scaleH = mh / base.height
  const cssScale = Math.min(Math.max(Math.min(scaleW, scaleH), 0.05), 4)
  const dpr = typeof window !== 'undefined' ? Math.min(window.devicePixelRatio || 1, 2) : 1
  const viewport = page.getViewport({ scale: cssScale * dpr })
  canvas.width = Math.floor(viewport.width)
  canvas.height = Math.floor(viewport.height)
  canvas.style.width = `${Math.floor(viewport.width / dpr)}px`
  canvas.style.height = `${Math.floor(viewport.height / dpr)}px`
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.setTransform(1, 0, 0, 1, 0, 0)
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  await page.render({ canvasContext: ctx, viewport }).promise
}
