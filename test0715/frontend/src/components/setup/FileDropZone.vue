<template>
  <div class="dropzone-wrap">
    <!-- Empty: drop area -->
    <div
      v-if="!file"
      class="drop-zone"
      :class="{ dragging: isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
      @click="triggerInput"
    >
      <input
        ref="fileInput"
        type="file"
        :accept="accept"
        class="hidden-input"
        @change="onFileChange"
      />
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="drop-icon">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" stroke-linecap="round"/>
        <polyline points="17 8 12 3 7 8" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="12" y1="3" x2="12" y2="15" stroke-linecap="round"/>
      </svg>
      <p class="drop-text">拖拽文件或<span class="drop-link">点击选择</span></p>
      <p class="drop-hint">{{ acceptLabel }}</p>
    </div>

    <!-- File uploaded -->
    <div v-else class="file-state">
      <div class="file-card">
        <div class="file-ext" :style="{ background: extColor }">{{ extLabel }}</div>
        <div class="file-meta">
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">{{ formatSize(file.size) }}</span>
        </div>
        <button class="file-remove" @click="$emit('remove')" title="移除">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <!-- Analyzing -->
      <div v-if="isAnalyzing" class="status-bar analyzing">
        <span class="status-spinner"></span>
        <span>AI 正在解析文件内容…</span>
      </div>

      <!-- Done -->
      <div v-else-if="analysisResult" class="status-bar done">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="20 6 9 17 4 12" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>已识别：{{ analysisResult.lesson_topic }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  accept: { type: String, default: '*' },
  acceptLabel: { type: String, default: '支持常见文档格式' },
  file: { type: Object, default: null },
  isAnalyzing: { type: Boolean, default: false },
  analysisResult: { type: Object, default: null },
})

const emit = defineEmits(['upload', 'remove'])

const fileInput = ref(null)
const isDragging = ref(false)

const extLabel = computed(() => {
  if (!props.file) return ''
  return props.file.name.split('.').pop().toUpperCase().slice(0, 4)
})

const extColor = computed(() => {
  const ext = extLabel.value
  if (ext === 'PDF') return '#FEE2E2'
  if (['PPT', 'PPTX'].includes(ext)) return '#FEF3C7'
  if (['DOC', 'DOCX'].includes(ext)) return '#DBEAFE'
  return '#F3F4F6'
})

function triggerInput() { fileInput.value?.click() }

function onFileChange(e) {
  const f = e.target.files[0]
  if (f) emit('upload', f)
}

function onDrop(e) {
  isDragging.value = false
  const f = e.dataTransfer.files[0]
  if (f) emit('upload', f)
}

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<style scoped>
.dropzone-wrap { width: 100%; }

.drop-zone {
  border: 1.5px dashed var(--color-border);
  border-radius: var(--radius-md);
  padding: 22px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--color-bg);
}

.drop-zone:hover,
.drop-zone.dragging {
  border-color: var(--color-blue);
  background: var(--color-blue-light);
}

.hidden-input { display: none; }

.drop-icon {
  color: var(--color-text-muted);
  margin: 0 auto 10px;
  display: block;
}

.drop-text {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}

.drop-link { color: var(--color-blue); font-weight: 600; }

.drop-hint { font-size: 11.5px; color: var(--color-text-muted); }

/* File state */
.file-state { display: flex; flex-direction: column; gap: 8px; }

.file-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.file-ext {
  width: 34px;
  height: 34px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 700;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.file-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-name {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-size { font-size: 11px; color: var(--color-text-muted); }

.file-remove {
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.file-remove:hover {
  background: var(--color-red-light);
  color: var(--color-red);
}

/* Status bars */
.status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: var(--radius-md);
  font-size: 12.5px;
  font-weight: 500;
}

.status-bar.analyzing {
  background: #FFFBEB;
  border: 1px solid #FDE68A;
  color: #92400E;
}

.status-bar.done {
  background: var(--color-green-light);
  border: 1px solid #A7F3D0;
  color: #065F46;
}

.status-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid #FDE68A;
  border-top-color: #F59E0B;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
