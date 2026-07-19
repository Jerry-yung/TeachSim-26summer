<template>
  <div class="step-goals">
    <div class="goals-intro">
      <p class="goals-desc">
        选择您在本次课堂中希望重点练习的方向。课后报告将针对您勾选的目标进行<strong>定向深度分析</strong>。
      </p>
    </div>

    <!-- Predefined goal tags -->
    <div class="goals-section">
      <span class="section-label">常见练习重点</span>
      <div class="tags-wrap">
        <button
          v-for="tag in GOAL_TAGS"
          :key="tag.value"
          class="goal-tag"
          :class="{ selected: store.selectedGoalTags.includes(tag.value) }"
          @click="store.toggleGoalTag(tag.value)"
        >
          <span class="tag-emoji">{{ tag.emoji }}</span>
          {{ tag.label }}
        </button>
      </div>
    </div>

    <!-- Custom text goal -->
    <div class="goals-section">
      <span class="section-label">自定义目标（选填）</span>
      <textarea
        v-model="store.customGoalText"
        class="custom-textarea"
        placeholder="例如：我总是在讲完一个知识点后不知道怎么过渡，或者提问后学生沉默时会很慌张……"
        rows="3"
      />
      <p class="textarea-hint">AI 将在课后报告中，针对您描述的具体问题给出定向建议</p>
    </div>

    <!-- Preview if filled -->
    <div v-if="store.hasCustomGoal" class="goal-preview animate-fadeInUp">
      <span class="preview-icon">🎯</span>
      <div class="preview-body">
        <span class="preview-label">本次练习目标已设置</span>
        <span class="preview-value">{{ store.goalSummary }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useLessonStore } from '@/stores/lessonStore.js'

const store = useLessonStore()

const GOAL_TAGS = [
  { value: '课堂节奏', label: '课堂节奏', emoji: '⏱️' },
  { value: '知识点衔接', label: '知识点衔接', emoji: '🔗' },
  { value: '提问质量', label: '提问质量', emoji: '❓' },
  { value: '语言表达', label: '语言表达', emoji: '🗣️' },
  { value: '课堂互动', label: '课堂互动', emoji: '🙋' },
  { value: '时间分配', label: '时间分配', emoji: '📊' },
  { value: '情绪管理', label: '情绪管理', emoji: '😌' },
  { value: '板书与讲解配合', label: '板书配合', emoji: '✏️' },
]
</script>

<style scoped>
.step-goals {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.goals-intro {
  padding: 12px 14px;
  background: var(--color-blue-light);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-blue);
}

.goals-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.goals-desc strong {
  color: var(--color-blue);
}

.goals-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
}

.tags-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.goal-tag {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px 14px;
  border-radius: var(--radius-full);
  border: 1.5px solid var(--color-border);
  background: var(--color-card);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.goal-tag:hover {
  border-color: #6366F1;
  color: #6366F1;
  background: #EEF2FF;
}

.goal-tag.selected {
  border-color: #6366F1;
  background: #6366F1;
  color: white;
}

.tag-emoji {
  font-size: 14px;
}

.custom-textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-card);
  color: var(--color-text);
  font-size: 13.5px;
  line-height: 1.6;
  resize: vertical;
  transition: border-color 0.15s;
  outline: none;
}

.custom-textarea:focus {
  border-color: #6366F1;
  box-shadow: 0 0 0 3px #EEF2FF;
}

.custom-textarea::placeholder {
  color: var(--color-text-muted);
}

.textarea-hint {
  font-size: 11.5px;
  color: var(--color-text-muted);
  margin-top: -4px;
}

.goal-preview {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  background: #F5F3FF;
  border: 1px solid #DDD6FE;
  border-radius: var(--radius-md);
}

.preview-icon {
  font-size: 18px;
  flex-shrink: 0;
  margin-top: 1px;
}

.preview-body {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.preview-label {
  font-size: 12px;
  font-weight: 600;
  color: #7C3AED;
}

.preview-value {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}
</style>
