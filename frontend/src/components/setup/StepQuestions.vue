<template>
  <div class="step-questions">
    <template v-for="(question, qi) in questions" :key="question.id">
      <div class="question-block animate-fadeInUp" :style="{ animationDelay: `${qi * 60}ms` }">
        <div class="question-header">
          <span class="question-label">{{ question.label }}</span>
          <span v-if="question.required" class="required-badge">必填</span>
          <span v-if="question.hint" class="question-hint">{{ question.hint }}</span>
        </div>

        <!-- Radio options -->
        <div v-if="question.type === 'radio'" class="options-row">
          <button
            v-for="opt in question.options"
            :key="opt"
            class="option-chip"
            :class="{ selected: answers[question.id] === opt }"
            @click="select(question.id, opt)"
          >
            <span v-if="answers[question.id] === opt" class="chip-check">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
            {{ opt }}
          </button>
        </div>

        <!-- Checkbox options -->
        <div v-if="question.type === 'checkbox'" class="options-row">
          <button
            v-for="opt in question.options"
            :key="opt"
            class="option-chip"
            :class="{ selected: isChecked(question.id, opt) }"
            @click="toggleCheck(question.id, opt)"
          >
            <span v-if="isChecked(question.id, opt)" class="chip-check">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
            {{ opt }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { useLessonStore } from '@/stores/lessonStore.js'

const props = defineProps({
  questions: { type: Array, default: () => [] },
})

const store = useLessonStore()
const { answers } = store

function select(questionId, value) {
  store.setAnswer(questionId, value)
}

function isChecked(questionId, value) {
  const current = store.answers[questionId]
  if (!Array.isArray(current)) return false
  return current.includes(value)
}

function toggleCheck(questionId, value) {
  const current = store.answers[questionId] || []
  if (current.includes(value)) {
    store.setAnswer(questionId, current.filter((v) => v !== value))
  } else {
    store.setAnswer(questionId, [...current, value])
  }
}
</script>

<style scoped>
.step-questions {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.question-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
  animation: fadeInUp 0.35s ease both;
}

.question-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.question-label {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-text);
}

.required-badge {
  font-size: 10px;
  font-weight: 600;
  color: var(--color-blue);
  background: var(--color-blue-light);
  padding: 2px 6px;
  border-radius: var(--radius-full);
}

.question-hint {
  font-size: 12px;
  color: var(--color-text-muted);
}

.options-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.option-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 7px 14px;
  border-radius: var(--radius-full);
  border: 1.5px solid var(--color-border);
  background: var(--color-card);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.option-chip:hover {
  border-color: var(--color-blue);
  color: var(--color-blue);
  background: var(--color-blue-light);
}

.option-chip.selected {
  border-color: var(--color-blue);
  background: var(--color-blue);
  color: white;
  font-weight: 600;
}

.chip-check {
  display: flex;
  align-items: center;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
