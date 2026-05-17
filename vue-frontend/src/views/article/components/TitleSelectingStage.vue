<template>
  <div class="title-selecting-stage">
    <div class="stage-header">
      <h2 class="stage-title">选择标题方案</h2>
      <p class="stage-subtitle">AI 为您生成了以下标题，请选择一个或自定义</p>
    </div>

    <a-radio-group v-model:value="selectedIndex" class="title-options">
      <div v-for="(option, index) in titleOptions" :key="index" class="title-option">
        <a-radio :value="index">
          <div class="title-content">
            <div class="title-main">{{ option.mainTitle }}</div>
            <div class="title-sub">{{ option.subTitle }}</div>
          </div>
        </a-radio>
      </div>
      <div class="title-option custom">
        <a-radio :value="-1">
          <div class="title-content">
            <div class="title-main">自定义标题</div>
          </div>
        </a-radio>
        <div v-if="selectedIndex === -1" class="custom-inputs">
          <a-input
            v-model:value="customMainTitle"
            placeholder="输入主标题"
            class="custom-input"
          />
          <a-input
            v-model:value="customSubTitle"
            placeholder="输入副标题"
            class="custom-input"
          />
        </div>
      </div>
    </a-radio-group>

    <div class="description-section">
      <label class="section-label">补充描述（可选）</label>
      <p class="section-tip">补充您对文章的期望、重点强调的内容等，AI 会在生成大纲时参考</p>
      <a-textarea
        v-model:value="userDescription"
        placeholder="例如：请重点强调技术原理，用通俗的语言讲解..."
        :rows="3"
        :maxlength="500"
        show-count
        class="description-textarea"
      />
    </div>

    <div class="actions">
      <a-button
        type="primary"
        size="large"
        :loading="loading"
        :disabled="!canConfirm"
        @click="handleConfirm"
        class="confirm-btn"
      >
        确认并生成大纲
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface TitleOption {
  mainTitle: string
  subTitle: string
}

interface Props {
  titleOptions: TitleOption[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
})

const emit = defineEmits<{
  (e: 'confirm', data: { mainTitle: string; subTitle: string; userDescription: string }): void
}>()

const selectedIndex = ref<number>(0)
const customMainTitle = ref('')
const customSubTitle = ref('')
const userDescription = ref('')

const canConfirm = computed(() => {
  if (selectedIndex.value === -1) {
    return customMainTitle.value.trim() && customSubTitle.value.trim()
  }
  return selectedIndex.value >= 0 && selectedIndex.value < props.titleOptions.length
})

function handleConfirm() {
  let mainTitle = ''
  let subTitle = ''
  if (selectedIndex.value === -1) {
    mainTitle = customMainTitle.value.trim()
    subTitle = customSubTitle.value.trim()
  } else {
    const selected = props.titleOptions[selectedIndex.value]
    mainTitle = selected.mainTitle
    subTitle = selected.subTitle
  }
  emit('confirm', { mainTitle, subTitle, userDescription: userDescription.value })
}
</script>

<style scoped>
.title-selecting-stage {
  padding: 16px;
  overflow-y: auto;
  height: 100%;
}
.stage-header {
  margin-bottom: 16px;
}
.stage-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 4px;
  color: #1a1a1a;
}
.stage-subtitle {
  font-size: 13px;
  color: #888;
  margin: 0;
}
.title-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
  width: 100%;
}
.title-option {
  border: 1.5px solid #e8e8e8;
  border-radius: 8px;
  padding: 12px 16px;
  transition: border-color 0.2s;
  cursor: pointer;
}
.title-option:hover {
  border-color: #4096ff;
}
:deep(.ant-radio-wrapper) {
  width: 100%;
  align-items: flex-start;
}
.title-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.title-main {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  line-height: 1.5;
}
.title-sub {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}
.custom.title-option {
  flex-direction: column;
}
.custom-inputs {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
  padding-left: 24px;
}
.custom-input {
  font-size: 13px;
}
.description-section {
  margin-bottom: 16px;
}
.section-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}
.section-tip {
  font-size: 12px;
  color: #999;
  margin: 0 0 8px;
}
.actions {
  display: flex;
  justify-content: flex-end;
}
.confirm-btn {
  min-width: 140px;
}
</style>
