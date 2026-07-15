<template>
  <div class="setup-view">
    <div class="setup-content">
      <div class="setup-header">
        <h1 class="setup-title">新建课堂配置</h1>
        <p class="setup-subtitle">直接开始即可模拟授课；上传教案或 PPT 后，AI 将结合文件内容为您提供更贴合实际的评价维度</p>
      </div>

      <!-- Step 1: Teacher context (free text, like PitchLab) -->
      <div class="setup-block">
        <div class="block-head">
          <div class="block-num">1</div>
          <div>
            <div class="block-title">
              描述您的教学背景
              <span class="optional-tag">选填</span>
            </div>
            <div class="block-desc">
              用自己的话介绍课程情况，AI 将提取信息并自动跳过相关提问，减少后续填写
            </div>
          </div>
        </div>

        <div class="context-card">
          <textarea
            v-model="store.teacherContext"
            class="context-textarea"
            :placeholder="contextPlaceholder"
            rows="5"
          />
          <div class="context-footer">
            <span class="context-hint">💡 请多给我们一些课堂线索，让我们为您量身定制最契合真实课堂的学情生态</span>
            <span class="context-count" :class="{ over: store.teacherContext.length > 400 }">
              {{ store.teacherContext.length }} / 500
            </span>
          </div>
        </div>
      </div>

      <!-- Step 2: Upload lesson plan -->
      <div class="setup-block">
        <div class="block-head">
          <div class="block-num" :class="{ done: !!store.uploadedFile }">
            <template v-if="store.uploadedFile">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3">
                <polyline points="20 6 9 17 4 12" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </template>
            <template v-else>2</template>
          </div>
          <div>
            <div class="block-title">
              上传教案 / PPT
              <span class="optional-tag">选填</span>
            </div>
            <div class="block-desc">支持 Word / PDF / PPT · 上传 PPT 后模拟上课时将在屏幕下半部展示供演示使用</div>
          </div>
        </div>

        <StepUpload />
      </div>
    </div>

    <!-- Right panel -->
    <div class="setup-panel-wrap">
      <SetupPanel @start="startInterview" />
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useLessonStore } from '@/stores/lessonStore.js'
import StepUpload from '@/components/setup/StepUpload.vue'
import SetupPanel from '@/components/setup/SetupPanel.vue'

const store = useLessonStore()
const router = useRouter()

const contextPlaceholder = `例如：我是一名高二语文老师，这节课准备讲六国论。班里是普通班，学生之前学过阿房宫赋和过秦论，整体基础偏弱。我最想练习的是课堂节奏——总是感觉过渡太生硬，讲完知识点不知道怎么自然地引入提问……`

function startInterview() {
  const sessionId = store.lessonId || `session-${Date.now()}`
  store.resetInterview()
  router.push(`/interview/${sessionId}`)
}
</script>

<style scoped>
.setup-view {
  display: flex;
  min-height: calc(100vh - 52px);
}

.setup-content {
  flex: 1;
  padding: 36px 40px 60px;
  max-width: 700px;
}

.setup-header {
  margin-bottom: 32px;
}

.setup-title {
  font-size: 23px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.5px;
  margin-bottom: 6px;
}

.setup-subtitle {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.setup-block {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  margin-bottom: 16px;
}

.block-head {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 20px 22px 16px;
  border-bottom: 1px solid var(--color-border-light);
}

.block-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-bg);
  border: 1.5px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
  transition: all 0.2s;
}

.block-num.done {
  background: var(--color-green);
  border-color: var(--color-green);
}

.block-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text);
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 3px;
}

.optional-tag {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  padding: 2px 7px;
  border-radius: var(--radius-full);
}

.block-desc {
  font-size: 12.5px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

/* Context textarea (PitchLab style) */
.context-card {
  padding: 16px 22px 14px;
}

.context-textarea {
  width: 100%;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  padding: 14px 16px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--color-text);
  resize: vertical;
  min-height: 110px;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.context-textarea:focus {
  border-color: var(--color-blue);
  background: white;
  box-shadow: 0 0 0 3px var(--color-blue-light);
}

.context-textarea::placeholder {
  color: var(--color-text-muted);
  font-size: 13.5px;
  line-height: 1.6;
}

.context-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.context-hint {
  font-size: 12px;
  color: var(--color-text-muted);
}

.context-count {
  font-size: 11.5px;
  color: var(--color-text-muted);
  font-variant-numeric: tabular-nums;
}

.context-count.over {
  color: var(--color-red);
}

/* Panel */
.setup-panel-wrap {
  width: 290px;
  min-width: 290px;
  padding: 36px 24px 36px 0;
  position: sticky;
  top: 0;
  height: calc(100vh - 52px);
  overflow-y: auto;
}
</style>
