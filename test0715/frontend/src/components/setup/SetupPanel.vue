<template>
  <div class="setup-panel">
    <div class="panel-header">
      <span class="panel-icon">🏫</span>
      <span class="panel-title">TeachSim</span>
    </div>

    <div class="panel-tagline">
      AI 陪您模拟一堂真实课堂，让您清晰看见自己的教学表现
    </div>

    <div class="panel-divider"></div>

    <ul class="panel-benefits">
      <li>
        <span class="benefit-icon">🎙️</span>
        <div>
          <span class="benefit-title">实时语音识别与 ASR 转写</span>
          <span class="benefit-desc">对着麦克风讲课，全程实时转写记录</span>
        </div>
      </li>
      <li>
        <span class="benefit-icon">🧑‍🎓</span>
        <div>
          <span class="benefit-title">AI 学生智能体实时互动</span>
          <span class="benefit-desc">模拟真实学生反应与课堂场景</span>
        </div>
      </li>
      <li>
        <span class="benefit-icon">📊</span>
        <div>
          <span class="benefit-title">课后多维度教学展示报告</span>
          <span class="benefit-desc">语速、互动、节奏、语言表达全面呈现</span>
        </div>
      </li>
      <li>
        <span class="benefit-icon">📑</span>
        <div>
          <span class="benefit-title">上传教案 / PPT</span>
          <span class="benefit-desc">上传 PPT 可在课堂下半屏演示；上传教案将纳入评价维度</span>
        </div>
      </li>
    </ul>

    <div class="panel-divider"></div>

    <button
      class="start-btn"
      :class="{ ready: store.canStart }"
      :disabled="!store.canStart"
      @click="$emit('start')"
    >
      <span v-if="store.isAnalyzing" class="btn-spinner"></span>
      <template v-else>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
          <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>
        开始模拟上课
      </template>
      <span v-if="store.isAnalyzing">AI 分析中…</span>
    </button>

    <p v-if="store.isAnalyzing" class="start-hint analyzing">AI 正在解读文件，请稍候…</p>
    <p v-else-if="store.hasPPT" class="start-hint ready-hint">✓ PPT 已就绪，课堂时将在下半屏演示</p>
    <p v-else-if="store.uploadedFile" class="start-hint ready-hint">✓ 教案已就绪，将纳入评价维度</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useLessonStore } from '@/stores/lessonStore.js'

const store = useLessonStore()
defineEmits(['start'])

const fileStatusIcon = computed(() => {
  if (store.isAnalyzing) return '⏳'
  if (store.hasPPT) return '🖼️'
  if (store.uploadedFile) return '📄'
  return '💡'
})

const fileStatusText = computed(() => {
  if (store.isAnalyzing) return 'AI 正在分析文件内容…'
  if (store.hasPPT) return '已上传 PPT，模拟课堂时将在屏幕下半部展示'
  if (store.uploadedFile) return '已上传教案，将纳入本次评价维度'
  return '未上传文件，也可直接开始——采用通用评价方式'
})

const fileStatusCls = computed(() => {
  if (store.isAnalyzing) return 'status-analyzing'
  if (store.uploadedFile) return 'status-ready'
  return 'status-empty'
})
</script>

<style scoped>
.setup-panel {
  background: #111827;
  border-radius: var(--radius-xl);
  padding: 26px 22px;
  color: white;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.panel-icon { font-size: 20px; }

.panel-title {
  font-size: 15px;
  font-weight: 700;
  color: white;
  letter-spacing: -0.3px;
}

.panel-tagline {
  font-size: 12.5px;
  color: rgba(255,255,255,0.5);
  line-height: 1.5;
  margin-bottom: 18px;
}

.panel-divider {
  height: 1px;
  background: rgba(255,255,255,0.1);
  margin-bottom: 18px;
}

.panel-benefits {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}

.panel-benefits li {
  display: flex;
  align-items: flex-start;
  gap: 11px;
}

.benefit-icon {
  font-size: 18px;
  flex-shrink: 0;
  margin-top: 1px;
}

.benefit-title {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: rgba(255,255,255,0.88);
  margin-bottom: 3px;
  line-height: 1.3;
}

.benefit-desc {
  display: block;
  font-size: 11.5px;
  color: rgba(255,255,255,0.42);
  line-height: 1.5;
}

/* 文件状态提示条 */
.panel-file-status {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  font-size: 12px;
  line-height: 1.5;
  margin-bottom: 18px;
}

.file-status-icon { flex-shrink: 0; font-size: 14px; }

.status-empty {
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.45);
}

.status-ready {
  background: rgba(110,231,183,0.12);
  color: #6EE7B7;
  border: 1px solid rgba(110,231,183,0.25);
}

.status-analyzing {
  background: rgba(252,211,77,0.1);
  color: #FCD34D;
  border: 1px solid rgba(252,211,77,0.25);
}

.start-btn {
  width: 100%;
  padding: 13px;
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.35);
  font-size: 14px;
  font-weight: 700;
  cursor: not-allowed;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: none;
  letter-spacing: -0.2px;
  margin-bottom: 10px;
}

.start-btn.ready {
  background: white;
  color: #111827;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(255,255,255,0.12);
}

.start-btn.ready:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 22px rgba(255,255,255,0.18);
}

.btn-spinner {
  width: 15px;
  height: 15px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: rgba(255,255,255,0.8);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.start-hint {
  text-align: center;
  font-size: 11.5px;
  color: rgba(255,255,255,0.3);
  line-height: 1.5;
}

.start-hint.analyzing {
  color: #FCD34D;
}

.start-hint.ready-hint {
  color: #6EE7B7;
}
</style>
