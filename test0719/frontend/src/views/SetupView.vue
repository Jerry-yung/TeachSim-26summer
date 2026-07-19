<template>
  <div class="setup-view">
    <div class="setup-content">
      <div class="setup-header">
        <h1 class="setup-title">新建课堂配置</h1>
        <p class="setup-subtitle">上传材料或直接开始，AI 将为您生成定制化虚拟课堂</p>
      </div>

      <!-- Step 1: Teacher context -->
      <div class="setup-block material-block">
        <div class="block-head">
          <div class="block-num">1</div>
          <div>
            <div class="block-title">
              描述您的教学背景
            </div>
            <div class="block-desc">用自己的话介绍课程情况，AI 将提取关键信息并减少后续提问数量</div>
          </div>
        </div>
        <div class="context-card">
          <textarea
            v-model="store.teacherContext"
            class="context-textarea"
            :placeholder="contextPlaceholder"
            rows="4"
            maxlength="500"
          />
          <div class="context-footer">
            <span class="context-hint">💡 请多给我们一些课堂线索，让我们为您量身定制最契合真实课堂的学情生态</span>
            <span class="context-count" :class="{ over: store.teacherContext.length > 450 }">
              {{ store.teacherContext.length }} / 500
            </span>
          </div>
          <div class="preset-inline-card">
            <div class="preset-inline-title">预设问题模式</div>
            <div class="preset-inline-desc">可复用上一节课堂预设回答，或重新回答本节预设问题</div>
            <div class="preset-mode-wrap">
              <label class="preset-option">
                <input
                  type="radio"
                  name="presetMode"
                  value="reuse_latest"
                  v-model="presetMode"
                >
                <span class="preset-label">使用上一节课课堂预设</span>
              </label>
              <label class="preset-option">
                <input
                  type="radio"
                  name="presetMode"
                  value="reanswer"
                  v-model="presetMode"
                >
                <span class="preset-label">重新回答预设问题</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 2: 两个上传区域并排 -->
      <div class="setup-block">
        <div class="block-head">
          <div class="block-num">2</div>
          <div>
            <div class="block-title">
              上传教学材料
              <span class="optional-tag">选填</span>
            </div>
            <div class="block-desc">可只上传其中一种，也可两者都上传</div>
          </div>
        </div>

        <div class="upload-grid">
          <!-- 教案上传 -->
          <div class="upload-lane">
            <div class="lane-header">
              <span class="lane-icon">📄</span>
              <div>
                <span class="lane-title">教案 / 讲义</span>
                <span class="lane-desc">用于评估教学内容准确度与教案贴合度</span>
              </div>
            </div>
            <FileDropZone
              accept=".pdf,.doc,.docx,.md,.txt"
              accept-label="Word / PDF / Markdown / TXT"
              :file="store.uploadedLesson"
              :is-analyzing="store.isAnalyzing && !!store.uploadedLesson"
              :analysis-result="store.uploadedLesson ? store.analysisResult : null"
              @upload="store.uploadLessonFile"
              @remove="store.removeLesson"
            />
          </div>

          <!-- 分隔线 -->
          <div class="lane-divider">
            <span>或</span>
          </div>

          <!-- PPT 上传 -->
          <div class="upload-lane">
            <div class="lane-header">
              <span class="lane-icon">🖥️</span>
              <div>
                <span class="lane-title">PPT</span>
                <span class="lane-desc">供演示翻阅</span>
              </div>
            </div>
            <FileDropZone
              accept=".ppt,.pptx,.pdf"
              accept-label="PPT / PPTX / PDF"
              :file="store.uploadedPPT"
              :is-analyzing="store.isAnalyzing && !!store.uploadedPPT"
              :analysis-result="store.uploadedPPT ? store.analysisResult : null"
              @upload="store.uploadPPTFile"
              @remove="store.removePPT"
            />
          </div>
        </div>

        <!-- 无文件提示 -->
        <div v-if="!store.hasAnyFile" class="no-file-tip">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          不上传材料也可直接开始，系统将根据历史授课记录采用通用评价维度
        </div>
      </div>

    </div>

    <!-- Right panel -->
    <div class="setup-panel-wrap">
      <SetupPanel @start="startInterview" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useLessonStore } from '@/stores/lessonStore.js'
import FileDropZone from '@/components/setup/FileDropZone.vue'
import SetupPanel from '@/components/setup/SetupPanel.vue'

const store = useLessonStore()
const router = useRouter()

const contextPlaceholder = `例如：我是一名高二语文老师，这节课准备讲六国论。班里是普通班，学生之前学过阿房宫赋，基础一般。我最想练习课堂节奏——总感觉过渡太生硬……`
const presetMode = ref('reanswer')

async function startInterview() {
  // 清除上节课残留的 PPT/教案标志与旧 session，避免新课堂误显示旧模式或旧PPT
  store.prepareNewClassroom()

  const sessionId = store.lessonId || `session-${Date.now()}`
  if (presetMode.value === 'reuse_latest') {
    try {
      const ok = await store.applyLatestPresetAnswers()
      if (!ok) {
        window.alert('暂无可复用的上一节课堂预设，将进入重新回答流程。')
        store.resetInterview()
      }
    } catch (err) {
      window.alert(err?.message || '读取上一节课堂预设失败，将进入重新回答流程。')
      store.resetInterview()
    }
  } else {
    store.resetInterview()
  }
  router.push(`/interview/${sessionId}`)
}
</script>

<style scoped>
/*
 * 宽屏：新建课堂配置贴主区域左侧；右侧「开始模拟上课」卡片留在主区域右缘（margin-left:auto）。
 * 中间留白自然分隔两块，避免整坨居中。
 */
.setup-view {
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  gap: clamp(24px, 3vw, 40px);
  min-height: calc(100vh - 52px);
  padding: 0 clamp(16px, 3vw, 40px);
  box-sizing: border-box;
}

.setup-content {
  flex: 0 1 900px;
  min-width: 0;
  width: 100%;
  max-width: 900px;
  min-height: calc(100vh - 52px);
  padding: 28px 30px 6px;
}

.setup-header {
  margin-bottom: 28px;
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
}

.setup-block {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  margin-bottom: 16px;
}

/* 第二块（上传材料）整体加高，贴近你标注的高度 */
.material-block {
  min-height: 460px;
  display: flex;
  flex-direction: column;
}

.material-block .upload-grid {
  flex: 1;
  align-items: stretch;
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

/* Context */
.context-card { padding: 16px 22px 14px; }

.context-textarea {
  width: 100%;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  padding: 13px 15px;
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--color-text);
  resize: vertical;
  min-height: 96px;
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
  font-size: 13px;
}

.context-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
}

.context-hint { font-size: 12px; color: var(--color-text-muted); }
.context-count { font-size: 11.5px; color: var(--color-text-muted); }
.context-count.over { color: var(--color-red); }
.preset-inline-card {
  margin-top: 14px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  padding: 12px 14px;
}
.preset-inline-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text);
}
.preset-inline-desc {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 4px;
}

/* Upload grid */
.upload-grid {
  display: flex;
  gap: 0;
  padding: 20px 22px 16px;
  align-items: flex-start;
}

.upload-lane {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.lane-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.lane-icon { font-size: 20px; flex-shrink: 0; margin-top: 1px; }

.lane-title {
  display: block;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 3px;
}

.lane-desc {
  display: block;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.lane-divider {
  width: 48px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-top: 60px;
  gap: 8px;
}

.lane-divider::before,
.lane-divider::after {
  content: '';
  flex: 1;
  width: 1px;
  background: var(--color-border);
  max-height: 40px;
}

.lane-divider span {
  font-size: 11px;
  color: var(--color-text-muted);
  font-weight: 600;
}

/* No file tip */
.no-file-tip {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0 22px 16px;
  padding: 10px 14px;
  background: var(--color-bg);
  border-radius: var(--radius-md);
  font-size: 12.5px;
  color: var(--color-text-muted);
  border: 1px dashed var(--color-border);
}

/* Panel — 贴主区域右侧；窄屏由 media query 取消 auto 并纵向排列 */
.setup-panel-wrap {
  flex: 0 0 auto;
  width: 300px;
  margin-left: auto;
  position: sticky;
  top: 0;
  height: calc(100vh - 52px);
  display: flex;
  align-items: center;
  align-self: flex-start;
  overflow-y: auto;
  padding: 24px 0;
  box-sizing: border-box;
}

@media (max-width: 1100px) {
  .setup-view {
    flex-direction: column;
    justify-content: flex-start;
    align-items: stretch;
    gap: 0;
  }
  .setup-panel-wrap {
    margin-left: 0;
    width: 100%;
    max-width: 420px;
    align-self: center;
    height: auto;
    position: static;
    padding: 8px 0 28px;
  }
}

.preset-mode-wrap {
  padding: 10px 0 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.preset-option {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.preset-option input[type='radio'] {
  accent-color: var(--color-blue);
}

.preset-label {
  font-weight: 500;
}
</style>
