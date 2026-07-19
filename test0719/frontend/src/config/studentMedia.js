/**
 * 小明「默认坐姿写字」状态：可用 MP4 替换 SVG 动画。
 *
 * 回退方式（任选其一即可恢复矢量动画）：
 * 1) 将 ENABLE_XIAOMING_DEFAULT_IDLE_VIDEO 改为 false 并重新构建/刷新。
 * 2) 浏览器控制台执行：localStorage.setItem('smartteacher_xiaoming_idle_render','svg') 后刷新。
 * 3) 构建前设置环境变量 VITE_XIAOMING_IDLE_VIDEO=0（关闭视频分支）。
 * 4) 视频文件缺失或解码失败时组件会自动回退到 SVG。
 *
 * 请将素材「小明_默认状态.mp4」复制到：
 *   frontend/public/classroom-videos/xiaoming-default.mp4
 */
export const ENABLE_XIAOMING_DEFAULT_IDLE_VIDEO = false

export const XIAOMING_DEFAULT_IDLE_VIDEO_PATH = '/classroom-videos/xiaoming-default.mp4'

const LS_RENDER_MODE = 'smartteacher_xiaoming_idle_render'

export function getXiaomingIdleVideoSrc() {
  if (import.meta.env.VITE_XIAOMING_IDLE_VIDEO === '0') {
    return ''
  }
  if (!ENABLE_XIAOMING_DEFAULT_IDLE_VIDEO) {
    return ''
  }
  if (typeof window !== 'undefined' && window.localStorage?.getItem(LS_RENDER_MODE) === 'svg') {
    return ''
  }
  return XIAOMING_DEFAULT_IDLE_VIDEO_PATH
}
