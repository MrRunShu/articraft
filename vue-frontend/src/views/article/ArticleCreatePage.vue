<template>
  <a-layout class="create-page">
    <AppHeader />

    <a-layout-content class="main">
      <a-row :gutter="16" style="height:100%">
        <!-- 左栏：输入设置（仅在输入阶段显示完整表单） -->
        <a-col :span="6" class="panel">
          <a-card :title="t('article.create.settings')" :bordered="false">
            <a-form layout="vertical">
              <a-form-item :label="t('article.create.topicLabel')">
                <a-textarea
                  v-model:value="topic"
                  :placeholder="t('article.create.topicPlaceholder')"
                  :rows="4"
                  :disabled="currentPhase !== 'INPUT'"
                />
              </a-form-item>

              <a-form-item :label="t('article.create.styleLabel')">
                <div class="style-grid">
                  <div
                    v-for="s in ARTICLE_STYLES"
                    :key="s.value"
                    :class="['style-item', { active: selectedStyle === s.value }]"
                    @click="currentPhase === 'INPUT' && (selectedStyle = s.value)"
                  >
                    <span class="style-icon">{{ s.icon }}</span>
                    <span class="style-label">{{ t('article.create.styles.' + s.value) }}</span>
                  </div>
                </div>
              </a-form-item>

              <a-form-item :label="t('article.create.imageMethodsLabel')">
                <div class="image-methods">
                  <div
                    v-for="m in IMAGE_METHODS"
                    :key="m.value"
                    :class="['method-item', { selected: enabledImageMethods.includes(m.value), locked: m.vipOnly && !userStore.isVip }]"
                    @click="toggleImageMethod(m)"
                  >
                    <span class="method-icon">{{ m.icon }}</span>
                    <span class="method-name">{{ t('article.create.imageMethodLabels.' + m.value) }}</span>
                    <a-tag v-if="m.vipOnly && !userStore.isVip" color="gold" class="vip-tag">VIP</a-tag>
                  </div>
                </div>
              </a-form-item>

              <a-alert
                v-if="!userStore.isVip"
                type="info"
                show-icon
                class="quota-alert"
              >
                <template #message>
                  {{ t('article.create.quotaAlert') }}
                  <a-button type="link" size="small" @click="router.push('/vip')">{{ t('article.create.upgradeVip') }}</a-button>
                </template>
              </a-alert>

              <a-form-item v-if="currentPhase === 'INPUT'">
                <a-button
                  type="primary"
                  block
                  :loading="isCreating"
                  :disabled="!topic.trim() || isCreating"
                  @click="onGenerate"
                >
                  {{ isCreating ? t('article.create.generating') : t('article.create.startBtn') }}
                </a-button>
              </a-form-item>

              <a-form-item v-if="currentPhase !== 'INPUT'">
                <a-button block @click="resetCreate">{{ t('article.create.restartBtn') }}</a-button>
              </a-form-item>
            </a-form>

            <a-divider v-if="taskId" />
            <div v-if="taskId" class="task-info">
              <div class="task-id">{{ t('article.create.taskId') }}：{{ taskId.slice(0, 8) }}...</div>
              <a-tag :color="statusColor">{{ statusText }}</a-tag>
            </div>

            <!-- 阶段进度指示器 -->
            <div v-if="currentPhase !== 'INPUT'" class="phase-steps">
              <a-divider />
              <div
                v-for="step in PHASE_STEPS"
                :key="step.key"
                :class="['phase-step', { active: currentPhase === step.key, done: isPhoneDone(step.key) }]"
              >
                <span class="phase-dot">{{ isPhoneDone(step.key) ? '✅' : currentPhase === step.key ? '⏳' : '○' }}</span>
                <span class="phase-name">{{ t('article.create.phases.' + step.key) }}</span>
              </div>
            </div>
          </a-card>
        </a-col>

        <!-- 中栏：进度日志 -->
        <a-col :span="8" class="panel">
          <a-card :title="t('article.create.progress')" :bordered="false" class="log-card">
            <div ref="logContainer" class="log-container">
              <div v-for="(log, i) in logs" :key="i" class="log-item">
                <span class="log-icon">{{ log.icon }}</span>
                <span class="log-text">{{ log.text }}</span>
                <a-tag v-if="log.method" size="small" color="blue" class="method-tag">
                  {{ t('article.create.imageMethodLabels.' + log.method, log.method) }}
                </a-tag>
              </div>
              <div v-if="isCreating && logs.length === 0" class="log-empty">{{ t('article.create.waitingConnection') }}</div>
              <div v-if="!isCreating && logs.length === 0" class="log-empty">{{ t('article.create.noLogs') }}</div>
            </div>
          </a-card>
        </a-col>

        <!-- 右栏：阶段内容区 -->
        <a-col :span="10" class="panel">
          <a-card :bordered="false" class="preview-card">
            <template #title>
              <a-space>
                <span>{{ rightPanelTitle }}</span>
                <a-tag v-if="selectedStyle" color="purple">
                  {{ ARTICLE_STYLES.find(s => s.value === selectedStyle)?.icon }}
                  {{ t('article.create.styles.' + selectedStyle) }}
                </a-tag>
                <a-button
                  v-if="taskId && currentPhase === 'COMPLETED'"
                  size="small"
                  @click="router.push(`/article/${taskId}`)"
                >
                  {{ t('article.create.viewDetail') }}
                </a-button>
              </a-space>
            </template>

            <!-- 阶段切换（带过渡动画） -->
            <Transition name="fade-slide" mode="out-in">
              <!-- 输入阶段：空状态 -->
              <div v-if="currentPhase === 'INPUT'" key="input" class="empty-state">
                <a-empty :description="t('article.create.contentEmpty')" />
              </div>

              <!-- 标题生成中 -->
              <div v-else-if="currentPhase === 'TITLE_GENERATING'" key="title-gen" class="loading-stage">
                <a-spin size="large" />
                <h3>{{ t('article.create.titleGenerating') }}</h3>
                <p>{{ t('article.create.titleGeneratingDesc') }}</p>
              </div>

              <!-- 标题选择阶段 -->
              <TitleSelectingStage
                v-else-if="currentPhase === 'TITLE_SELECTING'"
                key="title-select"
                :title-options="titleOptions"
                :loading="confirmLoading"
                @confirm="handleConfirmTitle"
              />

              <!-- 大纲生成中（流式展示） -->
              <div v-else-if="currentPhase === 'OUTLINE_GENERATING'" key="outline-gen" class="outline-generating-state">
                <div v-if="article.mainTitle" class="preview-header">
                  <h1 class="article-title">{{ article.mainTitle }}</h1>
                  <p class="article-subtitle">{{ article.subTitle }}</p>
                </div>
                <div class="outline-preview">
                  <div class="outline-generating-label">
                    <a-spin size="small" />
                    <span>{{ t('article.create.outlineGenerating') }}</span>
                  </div>
                  <div v-if="parsedOutline.length > 0" class="outline-list">
                    <div v-for="item in parsedOutline" :key="item.section" class="outline-item">
                      <div class="outline-item-title">{{ item.section }}. {{ item.title }}</div>
                      <ul class="outline-points">
                        <li v-for="(point, idx) in item.points" :key="idx">{{ point }}</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 大纲编辑阶段 -->
              <OutlineEditingStage
                v-else-if="currentPhase === 'OUTLINE_EDITING'"
                key="outline-edit"
                :outline="outline"
                :task-id="taskId"
                :loading="confirmLoading"
                @confirm="handleConfirmOutline"
              />

              <!-- 正文生成阶段 -->
              <div v-else-if="currentPhase === 'CONTENT_GENERATING'" key="content-gen" class="content-generating-state">
                <div v-if="article.mainTitle" class="preview-header">
                  <h1 class="article-title">{{ article.mainTitle }}</h1>
                  <p class="article-subtitle">{{ article.subTitle }}</p>
                </div>
                <div v-if="streamingContent" class="preview-content markdown-body" v-html="previewHtml" />
                <div v-else class="log-empty">{{ t('article.create.contentGenerating') }}</div>
              </div>

              <!-- 完成阶段 -->
              <div v-else-if="currentPhase === 'COMPLETED'" key="completed" class="completed-state">
                <div v-if="article.mainTitle" class="preview-header">
                  <h1 class="article-title">{{ article.mainTitle }}</h1>
                  <p class="article-subtitle">{{ article.subTitle }}</p>
                </div>
                <div v-if="streamingContent" class="preview-content markdown-body" v-html="previewHtml" />
              </div>
            </Transition>
          </a-card>
        </a-col>
      </a-row>
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { useI18n } from 'vue-i18n'
import {
  createArticle,
  confirmTitle,
  confirmOutline,
  getArticleDetail,
  ARTICLE_STYLES,
  type TitleOption,
  type OutlineSection,
} from '@/api/article'
import { connectSse, type SseConnection } from '@/utils/sse'
import { renderMarkdown } from '@/utils/markdown'
import { useUserStore } from '@/stores/user'
import AppHeader from '@/components/AppHeader.vue'
import TitleSelectingStage from './components/TitleSelectingStage.vue'
import OutlineEditingStage from './components/OutlineEditingStage.vue'

const { t } = useI18n()

const IMAGE_METHODS = [
  { value: 'PEXELS', icon: '📷', vipOnly: false },
  { value: 'NANO_BANANA', icon: '🎨', vipOnly: true },
  { value: 'MERMAID', icon: '📊', vipOnly: false },
  { value: 'ICONIFY', icon: '🔷', vipOnly: false },
  { value: 'EMOJI_PACK', icon: '😄', vipOnly: false },
]

type Phase =
  | 'INPUT'
  | 'TITLE_GENERATING'
  | 'TITLE_SELECTING'
  | 'OUTLINE_GENERATING'
  | 'OUTLINE_EDITING'
  | 'CONTENT_GENERATING'
  | 'COMPLETED'

const PHASE_STEPS = [
  { key: 'TITLE_GENERATING' },
  { key: 'TITLE_SELECTING' },
  { key: 'OUTLINE_GENERATING' },
  { key: 'OUTLINE_EDITING' },
  { key: 'CONTENT_GENERATING' },
  { key: 'COMPLETED' },
] as const

const PHASE_ORDER = PHASE_STEPS.map(s => s.key)

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const topic = ref('')
const selectedStyle = ref('POPULAR')
const enabledImageMethods = ref<string[]>(['PEXELS', 'MERMAID', 'ICONIFY', 'EMOJI_PACK'])
const taskId = ref('')
const status = ref('')
const isCreating = ref(false)
const confirmLoading = ref(false)
const currentPhase = ref<Phase>('INPUT')

const logs = ref<{ icon: string; text: string; method?: string }[]>([])
const streamingContent = ref('')
const outlineRaw = ref('')
const logContainer = ref<HTMLElement | null>(null)

const titleOptions = ref<TitleOption[]>([])
const outline = ref<OutlineSection[]>([])

const article = ref({ mainTitle: '', subTitle: '' })

let sseConn: SseConnection | null = null
let reconnectAttempts = 0

const previewHtml = computed(() =>
  streamingContent.value ? renderMarkdown(streamingContent.value) : ''
)

const parsedOutline = computed<OutlineSection[]>(() => {
  if (!outlineRaw.value) return []
  try {
    const cleaned = outlineRaw.value.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim()
    const data = JSON.parse(cleaned)
    return data?.sections ?? []
  } catch {
    return []
  }
})

const rightPanelTitle = computed(() => t(`article.create.phaseTitle.${currentPhase.value}`))

const statusColor = computed(() => {
  const map: Record<string, string> = {
    PENDING: 'default',
    PROCESSING: 'processing',
    COMPLETED: 'success',
    FAILED: 'error',
  }
  return map[status.value] ?? 'default'
})

const statusText = computed(() => t(`article.list.status.${status.value}`, status.value))

function isPhoneDone(key: string): boolean {
  const currentIdx = PHASE_ORDER.indexOf(currentPhase.value as any)
  const stepIdx = PHASE_ORDER.indexOf(key as any)
  return stepIdx < currentIdx
}

function addLog(icon: string, text: string, method?: string) {
  logs.value.push({ icon, text, method })
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

function toggleImageMethod(m: { value: string; vipOnly: boolean }) {
  if (m.vipOnly && !userStore.isVip) {
    message.warning(t('article.create.vipOnly'))
    router.push('/vip')
    return
  }
  const idx = enabledImageMethods.value.indexOf(m.value)
  if (idx >= 0) {
    enabledImageMethods.value.splice(idx, 1)
  } else {
    enabledImageMethods.value.push(m.value)
  }
}

async function onGenerate() {
  if (!topic.value.trim()) return
  logs.value = []
  streamingContent.value = ''
  outlineRaw.value = ''
  isCreating.value = true
  status.value = 'PENDING'
  currentPhase.value = 'INPUT'

  try {
    const res = await createArticle({
      topic: topic.value.trim(),
      style: selectedStyle.value,
      enabledImageMethods: enabledImageMethods.value.length ? enabledImageMethods.value : undefined,
    })
    taskId.value = res.data
    status.value = 'PROCESSING'
    router.replace({ query: { taskId: res.data } })
    addLog('⏳', t('article.create.log.taskCreated'))
    startSse(res.data)
  } catch {
    isCreating.value = false
    status.value = 'FAILED'
  }
}

function startSse(id: string) {
  sseConn?.close()
  sseConn = connectSse(
    id,
    (type, payload) => {
      reconnectAttempts = 0
      handleSseMessage(type, payload)
    },
    () => {
      if (status.value === 'COMPLETED' || status.value === 'FAILED') return
      if (reconnectAttempts < 3) {
        reconnectAttempts++
        addLog('🔄', t('article.create.log.reconnecting', { n: reconnectAttempts, max: 3 }))
        setTimeout(() => startSse(id), 2000)
      } else {
        reconnectAttempts = 0
        addLog('❌', t('article.create.log.reconnectFailed'))
        isCreating.value = false
      }
    }
  )
}

function handleSseMessage(type: string, payload: string) {
  switch (type) {
    case 'AGENT1_COMPLETE':
      currentPhase.value = 'TITLE_GENERATING'
      addLog('⏳', t('article.create.log.generatingTitles'))
      break

    case 'TITLES_GENERATED': {
      try {
        const data = JSON.parse(payload)
        titleOptions.value = data.titleOptions ?? []
      } catch {
        // payload 可能就是裸 JSON 字符串
        try { titleOptions.value = JSON.parse(payload) } catch { /* ignore */ }
      }
      currentPhase.value = 'TITLE_SELECTING'
      isCreating.value = false
      addLog('✅', t('article.create.log.titlesReady', { count: titleOptions.value.length }))
      break
    }

    case 'AGENT2_STREAMING':
      currentPhase.value = 'OUTLINE_GENERATING'
      outlineRaw.value += payload
      break

    case 'AGENT2_COMPLETE':
      addLog('✅', t('article.create.log.outlineComplete'))
      break

    case 'OUTLINE_GENERATED': {
      try {
        const data = JSON.parse(payload)
        outline.value = data.outline ?? []
      } catch {
        try { outline.value = JSON.parse(payload) } catch { /* ignore */ }
      }
      currentPhase.value = 'OUTLINE_EDITING'
      isCreating.value = false
      addLog('✅', t('article.create.log.outlineReady'))
      break
    }

    case 'AGENT3_STREAMING':
      currentPhase.value = 'CONTENT_GENERATING'
      streamingContent.value += payload
      break

    case 'AGENT3_COMPLETE':
      addLog('✅', t('article.create.log.contentComplete'))
      break

    case 'AGENT4_COMPLETE':
      addLog('✅', t('article.create.log.imageRequirementsComplete'))
      break

    case 'IMAGE_COMPLETE':
      try {
        const img = JSON.parse(payload)
        addLog('🖼️', t('article.create.log.imageFetched', { title: img.sectionTitle || t('article.create.log.cover') }), img.method)
      } catch {
        addLog('🖼️', t('article.create.log.imageFetchedNoTitle'))
      }
      break

    case 'AGENT5_COMPLETE':
      addLog('✅', t('article.create.log.imagesComplete'))
      break

    case 'MERGE_COMPLETE':
      addLog('✅', t('article.create.log.mergeComplete'))
      break

    case 'ALL_COMPLETE':
      status.value = 'COMPLETED'
      isCreating.value = false
      currentPhase.value = 'COMPLETED'
      addLog('🎉', t('article.create.log.articleComplete'))
      sseConn?.close()
      getArticleDetail(taskId.value).then(res => {
        const full = res.data?.fullContent || res.data?.content
        if (full) streamingContent.value = full
      })
      break

    case 'ERROR':
      status.value = 'FAILED'
      isCreating.value = false
      addLog('❌', t('article.create.log.generationFailed', { msg: payload }))
      sseConn?.close()
      currentPhase.value = 'INPUT'
      break
  }
}

async function handleConfirmTitle(data: {
  mainTitle: string
  subTitle: string
  userDescription: string
}) {
  confirmLoading.value = true
  try {
    await confirmTitle({
      taskId: taskId.value,
      selectedMainTitle: data.mainTitle,
      selectedSubTitle: data.subTitle,
      userDescription: data.userDescription || undefined,
    })
    article.value.mainTitle = data.mainTitle
    article.value.subTitle = data.subTitle
    outlineRaw.value = ''
    isCreating.value = true
    addLog('✅', t('article.create.log.titleConfirmed'))
  } catch (err: any) {
    message.error(err?.message || t('article.create.confirmTitleError'))
  } finally {
    confirmLoading.value = false
  }
}

async function handleConfirmOutline(outlineData: OutlineSection[]) {
  confirmLoading.value = true
  try {
    await confirmOutline({ taskId: taskId.value, outline: outlineData })
    streamingContent.value = ''
    isCreating.value = true
    addLog('✅', t('article.create.log.outlineConfirmed'))
  } catch (err: any) {
    message.error(err?.message || t('article.create.confirmOutlineError'))
  } finally {
    confirmLoading.value = false
  }
}

function resetCreate() {
  sseConn?.close()
  sseConn = null
  reconnectAttempts = 0
  currentPhase.value = 'INPUT'
  topic.value = ''
  selectedStyle.value = 'POPULAR'
  enabledImageMethods.value = ['PEXELS', 'MERMAID', 'ICONIFY', 'EMOJI_PACK']
  titleOptions.value = []
  outline.value = []
  isCreating.value = false
  confirmLoading.value = false
  status.value = ''
  taskId.value = ''
  streamingContent.value = ''
  outlineRaw.value = ''
  logs.value = []
  article.value = { mainTitle: '', subTitle: '' }
  router.replace({ query: {} })
}

async function loadAndReconnect(id: string) {
  try {
    const res = await getArticleDetail(id)
    const art = res.data as any
    if (!art) return

    taskId.value = id
    status.value = art.status || ''
    topic.value = art.topic || ''
    selectedStyle.value = art.style || 'POPULAR'
    article.value = { mainTitle: art.mainTitle || '', subTitle: art.subTitle || '' }

    if (art.status === 'COMPLETED') {
      currentPhase.value = 'COMPLETED'
      const full = art.fullContent || art.content
      if (full) streamingContent.value = full
      addLog('✅', t('article.create.log.articleLoaded'))
    } else if (art.status === 'FAILED') {
      addLog('❌', t('article.create.log.prevFailed', { msg: art.errorMessage || t('common.unknownError') }))
    } else {
      // 直接从 REST 响应读 phase，无需等待 SSE round-trip
      if (art.phase === 'TITLE_SELECTING' && art.titleOptions?.length) {
        titleOptions.value = art.titleOptions
        currentPhase.value = 'TITLE_SELECTING'
        addLog('🔄', t('article.create.log.resumeTitleSelect', { count: titleOptions.value.length }))
      } else if (art.phase === 'OUTLINE_EDITING' && art.outline?.length) {
        outline.value = art.outline
        currentPhase.value = 'OUTLINE_EDITING'
        addLog('🔄', t('article.create.log.resumeOutlineEdit'))
      } else {
        isCreating.value = true
        addLog('🔄', t('article.create.log.resumingConnection'))
      }
      startSse(id)
    }
  } catch {
    router.replace({ query: {} })
  }
}

onMounted(() => {
  const qTaskId = route.query.taskId as string | undefined
  if (qTaskId) loadAndReconnect(qTaskId)
})

onUnmounted(() => {
  sseConn?.close()
})
</script>

<style scoped>
.create-page {
  min-height: 100vh;
  background: #f0f2f5;
}
.main {
  padding: 16px;
  height: calc(100vh - 64px);
  overflow: hidden;
}
.panel { height: 100%; }
.log-card,
.preview-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}
:deep(.ant-card-body) {
  flex: 1;
  overflow: hidden;
  padding: 12px 16px;
}
.log-container {
  height: calc(100vh - 200px);
  overflow-y: auto;
  padding: 4px 0;
}
.log-item {
  padding: 6px 0;
  line-height: 1.6;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.log-icon { margin-right: 4px; flex-shrink: 0; }
.log-text { flex: 1; }
.method-tag { flex-shrink: 0; font-size: 11px; }
.log-empty { color: #aaa; text-align: center; padding: 40px 0; }

.task-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.task-id { font-size: 12px; color: #888; }

/* 配图方式选择器 */
.image-methods {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}
.method-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  border: 1.5px solid #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
  user-select: none;
  position: relative;
}
.method-item:hover { border-color: #4096ff; }
.method-item.selected { border-color: #4096ff; background: #e6f4ff; color: #4096ff; }
.method-item.locked { opacity: 0.6; cursor: pointer; }
.method-icon { flex-shrink: 0; }
.method-name { flex: 1; }
.vip-tag { font-size: 10px; padding: 0 3px; }
.quota-alert { margin-bottom: 8px; font-size: 12px; }
:deep(.quota-alert .ant-alert-message) { font-size: 12px; }

/* 风格选择器 */
.style-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.style-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 4px;
  border: 1.5px solid #d9d9d9;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}
.style-item:hover { border-color: #4096ff; color: #4096ff; }
.style-item.active { border-color: #4096ff; background: #e6f4ff; color: #4096ff; }
.style-icon { font-size: 18px; line-height: 1.4; }
.style-label { font-size: 12px; margin-top: 2px; }

/* 阶段进度 */
.phase-steps { display: flex; flex-direction: column; gap: 8px; padding: 4px 0; }
.phase-step { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #bbb; }
.phase-step.active { color: #4096ff; font-weight: 600; }
.phase-step.done { color: #52c41a; }
.phase-dot { font-size: 14px; }
.phase-name { flex: 1; }

/* 右侧内容区 */
.empty-state { display: flex; align-items: center; justify-content: center; height: calc(100vh - 200px); }
.preview-content {
  height: calc(100vh - 200px);
  overflow-y: auto;
  padding: 0 4px;
}

.loading-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: calc(100vh - 200px);
  text-align: center;
  gap: 12px;
}
.loading-stage h3 { font-size: 18px; font-weight: 600; margin: 0; }
.loading-stage p { font-size: 13px; color: #888; margin: 0; }

.outline-generating-state {
  height: calc(100vh - 200px);
  overflow-y: auto;
  padding: 4px;
}
.preview-header { margin-bottom: 16px; }
.article-title { font-size: 20px; font-weight: 700; margin: 0 0 4px; }
.article-subtitle { font-size: 14px; color: #666; margin: 0; }

.outline-preview { border: 1px solid #e8e8e8; border-radius: 8px; padding: 12px; }
.outline-generating-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #4096ff;
  margin-bottom: 12px;
  font-weight: 600;
}
.outline-list { display: flex; flex-direction: column; gap: 10px; }
.outline-item { border-left: 3px solid #4096ff; padding-left: 10px; }
.outline-item-title { font-size: 14px; font-weight: 600; margin-bottom: 4px; }
.outline-points { margin: 0; padding-left: 16px; font-size: 12px; color: #666; }
.outline-points li { margin-bottom: 2px; }

.content-generating-state,
.completed-state {
  height: calc(100vh - 200px);
  overflow-y: auto;
}

/* 阶段切换过渡动画 */
.fade-slide-enter-active,
.fade-slide-leave-active { transition: all 0.25s ease; }
.fade-slide-enter-from { opacity: 0; transform: translateX(20px); }
.fade-slide-leave-to { opacity: 0; transform: translateX(-20px); }

/* Markdown 样式 */
:deep(.markdown-body) h1, :deep(.markdown-body) h2, :deep(.markdown-body) h3 {
  margin: 12px 0 8px;
  font-weight: 600;
}
:deep(.markdown-body) h2 { font-size: 16px; border-bottom: 1px solid #eee; padding-bottom: 4px; }
:deep(.markdown-body) p { margin: 6px 0; line-height: 1.7; }
:deep(.markdown-body) img { max-width: 100%; border-radius: 4px; margin: 8px 0; }
</style>
