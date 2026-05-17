<template>
  <a-layout class="create-page">
    <a-layout-header class="header">
      <span class="logo">AI 爆款文章创作器</span>
      <a-space>
        <a-button type="link" style="color:#fff" @click="router.push('/article/list')">我的文章</a-button>
        <a-dropdown>
          <a-space style="color:#fff;cursor:pointer">
            <a-avatar>{{ userStore.userInfo?.userName?.charAt(0) ?? 'U' }}</a-avatar>
            <span>{{ userStore.userInfo?.userName }}</span>
          </a-space>
          <template #overlay>
            <a-menu>
              <a-menu-item @click="onLogout">退出登录</a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </a-space>
    </a-layout-header>

    <a-layout-content class="main">
      <a-row :gutter="16" style="height:100%">
        <!-- 左栏：输入设置（仅在输入阶段显示完整表单） -->
        <a-col :span="6" class="panel">
          <a-card title="创作设置" :bordered="false">
            <a-form layout="vertical">
              <a-form-item label="文章选题">
                <a-textarea
                  v-model:value="topic"
                  placeholder="请输入文章选题，例如：年轻人如何在大城市低成本生活"
                  :rows="4"
                  :disabled="currentPhase !== 'INPUT'"
                />
              </a-form-item>

              <a-form-item label="文章风格">
                <div class="style-grid">
                  <div
                    v-for="s in ARTICLE_STYLES"
                    :key="s.value"
                    :class="['style-item', { active: selectedStyle === s.value }]"
                    @click="currentPhase === 'INPUT' && (selectedStyle = s.value)"
                  >
                    <span class="style-icon">{{ s.icon }}</span>
                    <span class="style-label">{{ s.label }}</span>
                  </div>
                </div>
              </a-form-item>

              <a-form-item v-if="currentPhase === 'INPUT'">
                <a-button
                  type="primary"
                  block
                  :loading="isCreating"
                  :disabled="!topic.trim() || isCreating"
                  @click="onGenerate"
                >
                  {{ isCreating ? '生成中...' : '开始创作' }}
                </a-button>
              </a-form-item>

              <a-form-item v-if="currentPhase !== 'INPUT'">
                <a-button block @click="resetCreate">重新创作</a-button>
              </a-form-item>
            </a-form>

            <a-divider v-if="taskId" />
            <div v-if="taskId" class="task-info">
              <div class="task-id">任务 ID：{{ taskId.slice(0, 8) }}...</div>
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
                <span class="phase-name">{{ step.label }}</span>
              </div>
            </div>
          </a-card>
        </a-col>

        <!-- 中栏：进度日志 -->
        <a-col :span="8" class="panel">
          <a-card title="生成进度" :bordered="false" class="log-card">
            <div ref="logContainer" class="log-container">
              <div v-for="(log, i) in logs" :key="i" class="log-item">
                <span class="log-icon">{{ log.icon }}</span>
                <span class="log-text">{{ log.text }}</span>
                <a-tag v-if="log.method" size="small" color="blue" class="method-tag">
                  {{ IMAGE_METHOD_LABELS[log.method] ?? log.method }}
                </a-tag>
              </div>
              <div v-if="isCreating && logs.length === 0" class="log-empty">等待连接...</div>
              <div v-if="!isCreating && logs.length === 0" class="log-empty">点击「开始创作」启动生成</div>
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
                  {{ ARTICLE_STYLES.find(s => s.value === selectedStyle)?.label }}
                </a-tag>
                <a-button
                  v-if="taskId && currentPhase === 'COMPLETED'"
                  size="small"
                  @click="router.push(`/article/${taskId}`)"
                >
                  查看详情
                </a-button>
              </a-space>
            </template>

            <!-- 阶段切换（带过渡动画） -->
            <Transition name="fade-slide" mode="out-in">
              <!-- 输入阶段：空状态 -->
              <div v-if="currentPhase === 'INPUT'" key="input" class="empty-state">
                <a-empty description="文章内容将在这里显示" />
              </div>

              <!-- 标题生成中 -->
              <div v-else-if="currentPhase === 'TITLE_GENERATING'" key="title-gen" class="loading-stage">
                <a-spin size="large" />
                <h3>AI 正在生成标题方案...</h3>
                <p>稍等片刻，即将为您呈现多个精彩标题</p>
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
                    <span>AI 正在规划文章大纲...</span>
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
                <div v-else class="log-empty">正在生成正文...</div>
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
import { ref, computed, nextTick, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  createArticle,
  confirmTitle,
  confirmOutline,
  getArticleDetail,
  ARTICLE_STYLES,
  IMAGE_METHOD_LABELS,
  type TitleOption,
  type OutlineSection,
} from '@/api/article'
import { connectSse, type SseConnection } from '@/utils/sse'
import { renderMarkdown } from '@/utils/markdown'
import { useUserStore } from '@/stores/user'
import { userLogout } from '@/api/user'
import TitleSelectingStage from './components/TitleSelectingStage.vue'
import OutlineEditingStage from './components/OutlineEditingStage.vue'

type Phase =
  | 'INPUT'
  | 'TITLE_GENERATING'
  | 'TITLE_SELECTING'
  | 'OUTLINE_GENERATING'
  | 'OUTLINE_EDITING'
  | 'CONTENT_GENERATING'
  | 'COMPLETED'

const PHASE_STEPS = [
  { key: 'TITLE_GENERATING', label: '生成标题方案' },
  { key: 'TITLE_SELECTING', label: '选择标题' },
  { key: 'OUTLINE_GENERATING', label: '生成大纲' },
  { key: 'OUTLINE_EDITING', label: '编辑大纲' },
  { key: 'CONTENT_GENERATING', label: '生成正文' },
  { key: 'COMPLETED', label: '创作完成' },
] as const

const PHASE_ORDER = PHASE_STEPS.map(s => s.key)

const router = useRouter()
const userStore = useUserStore()

const topic = ref('')
const selectedStyle = ref('POPULAR')
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

const rightPanelTitle = computed(() => {
  const map: Record<Phase, string> = {
    INPUT: '文章预览',
    TITLE_GENERATING: '标题生成中',
    TITLE_SELECTING: '选择标题',
    OUTLINE_GENERATING: '大纲生成中',
    OUTLINE_EDITING: '编辑大纲',
    CONTENT_GENERATING: '正文生成中',
    COMPLETED: '文章预览',
  }
  return map[currentPhase.value] ?? '文章预览'
})

const statusColor = computed(() => {
  const map: Record<string, string> = {
    PENDING: 'default',
    PROCESSING: 'processing',
    COMPLETED: 'success',
    FAILED: 'error',
  }
  return map[status.value] ?? 'default'
})

const statusText = computed(() => {
  const map: Record<string, string> = {
    PENDING: '排队中',
    PROCESSING: '生成中',
    COMPLETED: '已完成',
    FAILED: '失败',
  }
  return map[status.value] ?? status.value
})

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

async function onGenerate() {
  if (!topic.value.trim()) return
  logs.value = []
  streamingContent.value = ''
  outlineRaw.value = ''
  isCreating.value = true
  status.value = 'PENDING'
  currentPhase.value = 'INPUT'

  try {
    const res = await createArticle({ topic: topic.value.trim(), style: selectedStyle.value })
    taskId.value = res.data
    status.value = 'PROCESSING'
    addLog('⏳', '任务创建成功，正在连接进度流...')
    startSse(res.data)
  } catch {
    isCreating.value = false
    status.value = 'FAILED'
  }
}

function startSse(id: string) {
  sseConn = connectSse(
    id,
    (type, payload) => handleSseMessage(type, payload),
    () => {
      if (status.value !== 'COMPLETED') {
        addLog('❌', 'SSE 连接断开')
        isCreating.value = false
      }
    }
  )
}

function handleSseMessage(type: string, payload: string) {
  switch (type) {
    case 'AGENT1_COMPLETE':
      currentPhase.value = 'TITLE_GENERATING'
      addLog('⏳', '正在生成标题方案...')
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
      addLog('✅', `标题方案已生成，共 ${titleOptions.value.length} 个，请选择`)
      break
    }

    case 'AGENT2_STREAMING':
      currentPhase.value = 'OUTLINE_GENERATING'
      outlineRaw.value += payload
      break

    case 'AGENT2_COMPLETE':
      addLog('✅', '大纲生成完成')
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
      addLog('✅', '大纲生成完成，请编辑确认')
      break
    }

    case 'AGENT3_STREAMING':
      currentPhase.value = 'CONTENT_GENERATING'
      streamingContent.value += payload
      break

    case 'AGENT3_COMPLETE':
      addLog('✅', '正文生成完成')
      break

    case 'AGENT4_COMPLETE':
      addLog('✅', '配图需求分析完成')
      break

    case 'IMAGE_COMPLETE':
      try {
        const img = JSON.parse(payload)
        addLog('🖼️', `配图就绪：${img.sectionTitle || '封面'}`, img.method)
      } catch {
        addLog('🖼️', '配图就绪')
      }
      break

    case 'AGENT5_COMPLETE':
      addLog('✅', '全部配图获取完成')
      break

    case 'MERGE_COMPLETE':
      addLog('✅', '图文合成完成')
      break

    case 'ALL_COMPLETE':
      status.value = 'COMPLETED'
      isCreating.value = false
      currentPhase.value = 'COMPLETED'
      addLog('🎉', '文章生成完成！')
      sseConn?.close()
      getArticleDetail(taskId.value).then(res => {
        const full = res.data?.fullContent || res.data?.content
        if (full) streamingContent.value = full
      })
      break

    case 'ERROR':
      status.value = 'FAILED'
      isCreating.value = false
      addLog('❌', `生成失败：${payload}`)
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
    addLog('✅', '标题已确认，正在生成大纲...')
  } catch (err: any) {
    message.error(err?.message || '确认标题失败')
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
    addLog('✅', '大纲已确认，正在生成正文...')
  } catch (err: any) {
    message.error(err?.message || '确认大纲失败')
  } finally {
    confirmLoading.value = false
  }
}

function resetCreate() {
  sseConn?.close()
  currentPhase.value = 'INPUT'
  topic.value = ''
  selectedStyle.value = 'POPULAR'
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
}

async function onLogout() {
  await userLogout()
  userStore.logout()
  message.success('已退出登录')
  router.push('/login')
}

onUnmounted(() => {
  sseConn?.close()
})
</script>

<style scoped>
.create-page {
  min-height: 100vh;
  background: #f0f2f5;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #001529;
  padding: 0 24px;
}
.logo {
  color: #fff;
  font-size: 18px;
  font-weight: bold;
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
