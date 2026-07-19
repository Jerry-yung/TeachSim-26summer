<template>
  <div class="step-upload">
    <!-- Drop zone -->
    <div
      v-if="!store.uploadedFile"
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
        accept=".pdf,.doc,.docx,.ppt,.pptx"
        class="hidden-input"
        @change="onFileChange"
      />
      <div class="drop-icon">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" stroke-linecap="round"/>
          <polyline points="17 8 12 3 7 8" stroke-linecap="round" stroke-linejoin="round"/>
          <line x1="12" y1="3" x2="12" y2="15" stroke-linecap="round"/>
        </svg>
      </div>
      <p class="drop-title">拖拽教案文件至此，或<span class="drop-link">点击选择</span></p>
      <p class="drop-hint">支持 Word / PDF / PPT，文件大小不超过 20MB</p>
    </div>

    <!-- File uploaded: analyzing state -->
    <div v-else class="file-state">
      <div class="file-card">
        <div class="file-icon" :style="{ background: fileIconBg }">
          {{ fileExt }}
        </div>
        <div class="file-meta">
          <span class="file-name">{{ store.uploadedFile.name }}</span>
          <span class="file-size">{{ formatSize(store.uploadedFile.size) }}</span>
        </div>
        <button class="file-remove" @click="removeFile" title="重新上传">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <!-- Analyzing banner -->
      <div v-if="store.isAnalyzing" class="analyzing-banner">
        <span class="analyzing-spinner"></span>
        <span class="analyzing-text">AI 正在解读教案，提取知识点与课程信息…</span>
      </div>

      <!-- Analysis done -->
      <div v-else-if="store.analysisResult" class="analysis-result animate-fadeInUp">
        <span class="result-icon">{{ store.analysisResult.subject_icon }}</span>
        <div class="result-body">
          <span class="result-topic">{{ store.analysisResult.lesson_topic }}</span>
          <span class="result-subject">{{ store.analysisResult.subject }}</span>
        </div>
        <span class="result-check">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="20 6 9 17 4 12" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          已识别
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useLessonStore } from '@/stores/lessonStore.js'

const store = useLessonStore()
const fileInput = ref(null)
const isDragging = ref(false)

const fileExt = computed(() => {
  if (!store.uploadedFile) return ''
  return store.uploadedFile.name.split('.').pop().toUpperCase().slice(0, 3)
})

const fileIconBg = computed(() => {
  const ext = fileExt.value
  if (ext === 'PDF') return '#FEE2E2'
  if (['DOC', 'DOC'].includes(ext)) return '#DBEAFE'
  if (['PPT', 'PPX'].includes(ext)) return '#FEF3C7'
  return '#F3F4F6'
})

function triggerInput() {
  fileInput.value?.click()
}

function onFileChange(e) {
  const file = e.target.files[0]
  if (file) handleFile(file)
}

function onDrop(e) {
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) handleFile(file)
}

function handleFile(file) {
  store.uploadAndAnalyze(file)
}

function removeFile() {
  store.reset()
  if (fileInput.value) fileInput.value.value = ''
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<style scoped>
.drop-zone {
  border: 1.5px dashed var(--color-border);
  border-radius: var(--radius-lg);
  padding: 40px 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--color-bg);
}

.drop-zone:hover,
.drop-zone.dragging {
  border-color: var(--color-blue);
  background: var(--color-blue-light);
}

.hidden-input {
  display: none;
}

.drop-icon {
  color: var(--color-text-muted);
  margin-bottom: 14px;
  display: flex;
  justify-content: center;
}

.drop-title {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.drop-link {
  color: var(--color-blue);
  font-weight: 600;
}

.drop-hint {
  font-size: 12px;
  color: var(--color-text-muted);
}

.file-state {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.file-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.file-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.file-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.file-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-size {
  font-size: 11px;
  color: var(--color-text-muted);
}

.file-remove {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  transition: all 0.15s;
  flex-shrink: 0;
}

.file-remove:hover {
  background: var(--color-red-light);
  color: var(--color-red);
}

.analyzing-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  background: #FFFBEB;
  border: 1px solid #FDE68A;
  border-radius: var(--radius-md);
}

.analyzing-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #FDE68A;
  border-top-color: #F59E0B;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

.analyzing-text {
  font-size: 13px;
  color: #92400E;
  font-weight: 500;
}

.analysis-result {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: var(--color-green-light);
  border: 1px solid #A7F3D0;
  border-radius: var(--radius-md);
}

.result-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.result-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.result-topic {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

.result-subject {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.result-check {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-green);
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
