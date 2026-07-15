<template>
  <div class="classroom-shell" :class="{ 'has-ppt': store.hasPPT }">

    <!-- 全屏模拟课堂区域 -->
    <div class="classroom-area">
      <div class="placeholder-card">
        <div class="placeholder-icon">🏫</div>
        <h2>虚拟课堂</h2>
        <p>课堂模拟模块正在开发中（阶段 3-5）</p>
        <p class="sub">包含：麦克风录音 · VAD 断句 · WebSocket · 虚拟学生动画 · TTS 播放</p>

        <!-- 根据文件状态显示不同提示 -->
        <div class="mode-badge" :class="modeBadgeCls">
          {{ modeBadgeText }}
        </div>

        <div class="placeholder-actions">
          <router-link to="/setup" class="btn-secondary">← 返回配置页</router-link>
          <router-link to="/report/mock-session-001" class="btn-primary">查看示例报告 →</router-link>
        </div>
      </div>
    </div>

    <!-- PPT 展示区：仅当上传了 PPT 时才显示，占据下半屏 -->
    <div v-if="store.hasPPT" class="ppt-area">
      <div class="ppt-bar">
        <span class="ppt-bar-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="20" height="14" rx="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
          {{ store.uploadedFile?.name }}
        </span>
        <div class="ppt-nav">
          <button class="ppt-btn">‹ 上一页</button>
          <span class="ppt-page">第 1 / ? 页</span>
          <button class="ppt-btn">下一页 ›</button>
        </div>
      </div>
      <div class="ppt-preview">
        <div class="ppt-placeholder">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <rect x="2" y="3" width="20" height="14" rx="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
          <p>PPT 渲染区域（待集成）</p>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useLessonStore } from '@/stores/lessonStore.js'

const store = useLessonStore()

const modeBadgeText = computed(() => {
  if (store.hasPPT) return '🖼️ PPT 模式 · 教案已在下方展示'
  if (store.uploadedFile) return '📄 教案模式 · 评价维度已定制'
  return '🎙️ 自由讲课模式 · 通用评价维度'
})

const modeBadgeCls = computed(() => {
  if (store.hasPPT) return 'badge-ppt'
  if (store.uploadedFile) return 'badge-lesson'
  return 'badge-free'
})
</script>

<style scoped>
.classroom-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* 无 PPT 时，课堂区域全屏 */
.classroom-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  overflow: auto;
}

/* 有 PPT 时，课堂区占上半，PPT 占下半 */
.has-ppt .classroom-area {
  flex: 1 1 50%;
  min-height: 0;
  border-bottom: 2px solid var(--color-border);
}

.has-ppt .ppt-area {
  flex: 0 0 45%;
  min-height: 0;
}

.placeholder-card {
  text-align: center;
  max-width: 480px;
}

.placeholder-icon {
  font-size: 56px;
  margin-bottom: 20px;
}

h2 {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 10px;
}

p {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: 6px;
}

.sub {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-bottom: 18px;
}

.mode-badge {
  display: inline-block;
  font-size: 12.5px;
  font-weight: 600;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  margin-bottom: 24px;
}

.badge-free {
  background: #F3F4F6;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.badge-lesson {
  background: var(--color-blue-light);
  color: var(--color-blue);
  border: 1px solid #BFDBFE;
}

.badge-ppt {
  background: #FEF3C7;
  color: #92400E;
  border: 1px solid #FDE68A;
}

.placeholder-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-secondary,
.btn-primary {
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.15s;
}

.btn-secondary {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
}

.btn-secondary:hover {
  background: var(--color-border);
}

.btn-primary {
  background: var(--color-accent);
  color: white;
}

.btn-primary:hover {
  opacity: 0.85;
}

/* PPT 展示区 */
.ppt-area {
  display: flex;
  flex-direction: column;
  background: #1E1E2E;
  overflow: hidden;
}

.ppt-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #111827;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  flex-shrink: 0;
}

.ppt-bar-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(255,255,255,0.6);
  font-weight: 500;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ppt-nav {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ppt-btn {
  font-size: 12px;
  color: rgba(255,255,255,0.6);
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 6px;
  padding: 4px 10px;
  cursor: pointer;
  transition: all 0.15s;
}

.ppt-btn:hover {
  background: rgba(255,255,255,0.15);
  color: white;
}

.ppt-page {
  font-size: 12px;
  color: rgba(255,255,255,0.4);
  font-variant-numeric: tabular-nums;
}

.ppt-preview {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.ppt-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: rgba(255,255,255,0.2);
}

.ppt-placeholder p {
  font-size: 13px;
  color: rgba(255,255,255,0.2);
  margin: 0;
}
</style>
