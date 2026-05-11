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
        <!-- 左栏：输入 -->
        <a-col :span="6" class="panel">
          <a-card title="创作设置" :bordered="false">
            <a-form layout="vertical">
              <a-form-item label="文章选题">
                <a-textarea
                  v-model:value="topic"
                  placeholder="请输入文章选题，例如：年轻人如何在大城市低成本生活"
                  :rows="5"
                  :disabled="generating"
                />
              </a-form-item>
              <a-form-item>
                <a-button
                  type="primary"
                  block
                  :loading="generating"
                  :disabled="!topic.trim() || generating"
                  @click="onGenerate"
                >
                  {{ generating ? '生成中...' : '开始创作' }}
                </a-button>
              </a-form-item>
            </a-form>

            <a-divider v-if="taskId" />
            <div v-if="taskId" class="task-info">
              <div class="task-id">任务 ID：{{ taskId.slice(0, 8) }}...</div>
              <a-tag :color="statusColor">{{ statusText }}</a-tag>
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
              </div>
              <div v-if="generating && logs.length === 0" class="log-empty">
                等待连接...
              </div>
              <div v-if="!generating && logs.length === 0" class="log-empty">
                点击「开始创作」启动生成
              </div>
            </div>
          </a-card>
        </a-col>

        <!-- 右栏：文章预览 -->
        <a-col :span="10" class="panel">
          <a-card :bordered="false" class="preview-card">
            <template #title>
              <a-space>
                文章预览
                <a-button
                  v-if="taskId && status === 'COMPLETED'"
                  size="small"
                  @click="router.push(`/article/${taskId}`)"
                >
                  查看详情
                </a-button>
              </a-space>
            </template>
            <div v-if="previewHtml" class="preview-content markdown-body" v-html="previewHtml" />
            <a-empty v-else description="文章内容将在这里实时显示" />
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
import { createArticle } from '@/api/article'
import { connectSse, type SseConnection } from '@/utils/sse'
import { renderMarkdown } from '@/utils/markdown'
import { useUserStore } from '@/stores/user'
import { userLogout } from '@/api/user'

const router = useRouter()
const userStore = useUserStore()

const topic = ref('')
const taskId = ref('')
const status = ref('')
const generating = ref(false)
const logs = ref<{ icon: string; text: string }[]>([])
const streamingContent = ref('')
const logContainer = ref<HTMLElement | null>(null)

let sseConn: SseConnection | null = null

const previewHtml = computed(() =>
  streamingContent.value ? renderMarkdown(streamingContent.value) : ''
)

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

function addLog(icon: string, text: string) {
  logs.value.push({ icon, text })
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
  generating.value = true
  status.value = 'PENDING'

  try {
    const res = await createArticle(topic.value.trim())
    taskId.value = res.data
    status.value = 'PROCESSING'
    addLog('⏳', '任务创建成功，正在连接进度流...')
    startSse(res.data)
  } catch {
    generating.value = false
    status.value = 'FAILED'
  }
}

function startSse(id: string) {
  sseConn = connectSse(
    id,
    (type, payload) => {
      handleSseMessage(type, payload)
    },
    () => {
      if (status.value !== 'COMPLETED') {
        addLog('❌', 'SSE 连接断开')
        generating.value = false
      }
    }
  )
}

function handleSseMessage(type: string, payload: string) {
  switch (type) {
    case 'AGENT1_COMPLETE':
      status.value = 'PROCESSING'
      addLog('✅', '标题生成完成')
      break
    case 'AGENT2_STREAMING':
      break
    case 'AGENT2_COMPLETE':
      addLog('✅', '大纲生成完成')
      break
    case 'AGENT3_STREAMING':
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
        addLog('🖼️', `配图就绪：${img.sectionTitle || '封面'}`)
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
      generating.value = false
      addLog('🎉', '文章生成完成！')
      sseConn?.close()
      break
    case 'ERROR':
      status.value = 'FAILED'
      generating.value = false
      addLog('❌', `生成失败：${payload}`)
      sseConn?.close()
      break
  }
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
.panel {
  height: 100%;
}
.log-card,
.preview-card {
  height: 100%;
  display: flex;
  flex-direction: column;
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
}
.log-icon {
  margin-right: 8px;
}
.log-empty {
  color: #aaa;
  text-align: center;
  padding: 40px 0;
}
.preview-content {
  height: calc(100vh - 200px);
  overflow-y: auto;
  padding: 0 4px;
}
.task-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.task-id {
  font-size: 12px;
  color: #888;
}

/* 简单 markdown 样式 */
:deep(.markdown-body) h1,
:deep(.markdown-body) h2,
:deep(.markdown-body) h3 {
  margin: 12px 0 8px;
  font-weight: 600;
}
:deep(.markdown-body) h2 {
  font-size: 16px;
  border-bottom: 1px solid #eee;
  padding-bottom: 4px;
}
:deep(.markdown-body) p {
  margin: 6px 0;
  line-height: 1.7;
}
:deep(.markdown-body) img {
  max-width: 100%;
  border-radius: 4px;
  margin: 8px 0;
}
</style>
