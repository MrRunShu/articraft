<template>
  <div class="outline-editing-stage">
    <div class="stage-header">
      <h2 class="stage-title">{{ t('article.outlineEdit.title') }}</h2>
      <p class="stage-subtitle">{{ t('article.outlineEdit.subtitle') }}</p>
    </div>

    <div class="outline-list" ref="outlineListRef">
      <div
        v-for="(section, index) in outlineSections"
        :key="section.section"
        class="outline-section"
      >
        <div class="section-header">
          <span class="drag-handle" title="拖动排序">⋮⋮</span>
          <span class="section-number">{{ index + 1 }}</span>
          <a-input
            v-model:value="section.title"
            :placeholder="t('article.outlineEdit.sectionTitle')"
            class="section-title-input"
          />
          <a-button type="text" danger size="small" @click="deleteSection(index)">✕</a-button>
        </div>

        <div class="section-points">
          <div v-for="(_, pointIdx) in section.points" :key="pointIdx" class="point-item">
            <span class="point-bullet">•</span>
            <a-input
              v-model:value="section.points[pointIdx]"
              :placeholder="t('article.outlineEdit.pointContent')"
              class="point-input"
            />
            <a-button
              type="text"
              size="small"
              @click="deletePoint(index, pointIdx)"
              :disabled="section.points.length <= 1"
            >×</a-button>
          </div>
          <a-button type="dashed" size="small" @click="addPoint(index)" class="add-point-btn">
            {{ t('article.outlineEdit.addPoint') }}
          </a-button>
        </div>
      </div>
    </div>

    <div class="ai-chat-section">
      <div class="chat-header">{{ t('article.outlineEdit.aiAssistant') }}</div>
      <div class="chat-input-wrapper">
        <a-textarea
          v-model:value="modifySuggestion"
          :placeholder="t('article.outlineEdit.aiPlaceholder')"
          :rows="2"
          :maxlength="500"
          show-count
        />
        <a-button
          type="primary"
          :loading="aiModifying"
          :disabled="!modifySuggestion.trim()"
          @click="handleAiModify"
          class="ai-modify-btn"
        >
          {{ t('article.outlineEdit.aiModifyBtn') }}
        </a-button>
      </div>
    </div>

    <div class="actions">
      <a-button size="large" @click="addSection" class="add-section-btn">
        {{ t('article.outlineEdit.addSection') }}
      </a-button>
      <a-button
        type="primary"
        size="large"
        :loading="loading"
        :disabled="!canConfirm"
        @click="handleConfirm"
        class="confirm-btn"
      >
        {{ t('article.outlineEdit.confirmBtn') }}
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import { useI18n } from 'vue-i18n'
import Sortable from 'sortablejs'
import { aiModifyOutline } from '@/api/article'

interface OutlineSection {
  section: number
  title: string
  points: string[]
}

interface Props {
  outline: OutlineSection[]
  taskId: string
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), { loading: false })

const { t } = useI18n()

const emit = defineEmits<{
  (e: 'confirm', outline: OutlineSection[]): void
}>()

const outlineSections = ref<OutlineSection[]>(
  props.outline.map((item, index) => ({
    section: item.section ?? index + 1,
    title: item.title ?? '',
    points: item.points?.length ? [...item.points] : [''],
  }))
)
const outlineListRef = ref<HTMLElement | null>(null)
const modifySuggestion = ref('')
const aiModifying = ref(false)

const canConfirm = computed(() =>
  outlineSections.value.length > 0 &&
  outlineSections.value.every(
    s => s.title.trim() && s.points.length > 0 && s.points.every(p => p.trim())
  )
)

onMounted(() => {
  nextTick(() => {
    if (outlineListRef.value) {
      Sortable.create(outlineListRef.value, {
        animation: 150,
        handle: '.drag-handle',
        onEnd: ({ oldIndex, newIndex }) => {
          if (oldIndex !== undefined && newIndex !== undefined && oldIndex !== newIndex) {
            const item = outlineSections.value.splice(oldIndex, 1)[0]
            outlineSections.value.splice(newIndex, 0, item)
            outlineSections.value.forEach((s, i) => (s.section = i + 1))
          }
        },
      })
    }
  })
})

function addSection() {
  outlineSections.value.push({
    section: outlineSections.value.length + 1,
    title: '',
    points: [''],
  })
}

function deleteSection(index: number) {
  outlineSections.value.splice(index, 1)
  outlineSections.value.forEach((s, i) => (s.section = i + 1))
}

function addPoint(sectionIndex: number) {
  outlineSections.value[sectionIndex].points.push('')
}

function deletePoint(sectionIndex: number, pointIndex: number) {
  const section = outlineSections.value[sectionIndex]
  if (section.points.length > 1) {
    section.points.splice(pointIndex, 1)
  }
}

function handleConfirm() {
  emit('confirm', outlineSections.value)
}

async function handleAiModify() {
  if (!modifySuggestion.value.trim()) return
  aiModifying.value = true
  try {
    const res = await aiModifyOutline({
      taskId: props.taskId,
      modifySuggestion: modifySuggestion.value,
    })
    if (res.data) {
      outlineSections.value = res.data.map((item: OutlineSection, index: number) => ({
        section: item.section ?? index + 1,
        title: item.title ?? '',
        points: item.points?.length ? [...item.points] : [''],
      }))
      modifySuggestion.value = ''
      message.success(t('article.outlineEdit.aiSuccess'))
    }
  } catch (err: any) {
    message.error(err?.message || t('article.outlineEdit.aiFailed'))
  } finally {
    aiModifying.value = false
  }
}
</script>

<style scoped>
.outline-editing-stage {
  padding: 16px;
  overflow-y: auto;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.stage-header { margin-bottom: 4px; }
.stage-title { font-size: 18px; font-weight: 600; margin: 0 0 4px; }
.stage-subtitle { font-size: 13px; color: #888; margin: 0; }

.outline-list { display: flex; flex-direction: column; gap: 10px; }
.outline-section {
  border: 1.5px solid #e8e8e8;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
  transition: border-color 0.2s;
}
.outline-section:hover { border-color: #b0c4f0; }

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.drag-handle {
  cursor: grab;
  color: #bbb;
  font-size: 16px;
  flex-shrink: 0;
  user-select: none;
}
.drag-handle:active { cursor: grabbing; }
.section-number {
  font-size: 12px;
  font-weight: 700;
  color: #4096ff;
  background: #e6f4ff;
  border-radius: 4px;
  padding: 1px 6px;
  flex-shrink: 0;
}
.section-title-input { flex: 1; font-weight: 600; }

.section-points { padding-left: 32px; display: flex; flex-direction: column; gap: 6px; }
.point-item { display: flex; align-items: center; gap: 6px; }
.point-bullet { color: #aaa; flex-shrink: 0; }
.point-input { flex: 1; font-size: 13px; }
.add-point-btn { width: 100%; font-size: 12px; }

.ai-chat-section {
  border: 1.5px solid #d9d9d9;
  border-radius: 8px;
  padding: 12px;
  background: #fafafa;
}
.chat-header { font-size: 13px; font-weight: 600; margin-bottom: 8px; color: #555; }
.chat-input-wrapper { display: flex; gap: 8px; align-items: flex-end; }
.chat-input-wrapper :deep(.ant-input-textarea) { flex: 1; }
.ai-modify-btn { flex-shrink: 0; }

.actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 4px;
}
.confirm-btn { min-width: 140px; }
</style>
