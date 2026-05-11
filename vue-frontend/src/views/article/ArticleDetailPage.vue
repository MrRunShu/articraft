<template>
  <a-layout class="detail-page">
    <a-layout-header class="header">
      <span class="logo">AI 爆款文章创作器</span>
      <a-space>
        <a-button type="link" style="color:#fff" @click="router.push('/article/list')">我的文章</a-button>
        <a-button type="link" style="color:#fff" @click="router.push('/')">创作新文章</a-button>
      </a-space>
    </a-layout-header>

    <a-layout-content class="main">
      <a-spin :spinning="loading">
        <template v-if="article">
          <a-row :gutter="24">
            <!-- 左侧：元信息 + 操作 -->
            <a-col :span="6">
              <a-card :bordered="false">
                <a-descriptions layout="vertical" :column="1" size="small">
                  <a-descriptions-item label="状态">
                    <a-tag :color="statusColor">{{ statusText }}</a-tag>
                  </a-descriptions-item>
                  <a-descriptions-item label="选题">{{ article.topic }}</a-descriptions-item>
                  <a-descriptions-item v-if="article.mainTitle" label="主标题">
                    {{ article.mainTitle }}
                  </a-descriptions-item>
                  <a-descriptions-item v-if="article.subTitle" label="副标题">
                    {{ article.subTitle }}
                  </a-descriptions-item>
                  <a-descriptions-item label="创建时间">
                    {{ article.createTime?.slice(0, 16).replace('T', ' ') }}
                  </a-descriptions-item>
                  <a-descriptions-item v-if="article.completedTime" label="完成时间">
                    {{ article.completedTime?.slice(0, 16).replace('T', ' ') }}
                  </a-descriptions-item>
                </a-descriptions>

                <a-divider />

                <a-space direction="vertical" style="width:100%">
                  <a-button block @click="onExport" :disabled="!article.fullContent">
                    导出 Markdown
                  </a-button>
                  <a-button block @click="router.back()">返回</a-button>
                </a-space>
              </a-card>

              <!-- 封面图 -->
              <a-card v-if="article.coverImage" :bordered="false" style="margin-top:16px">
                <template #title>封面图</template>
                <img :src="article.coverImage" alt="封面" style="width:100%;border-radius:4px" />
              </a-card>
            </a-col>

            <!-- 右侧：文章内容 -->
            <a-col :span="18">
              <a-card :bordered="false">
                <template #title>
                  <div class="article-title">
                    <div v-if="article.mainTitle" class="main-title">{{ article.mainTitle }}</div>
                    <div v-if="article.subTitle" class="sub-title">{{ article.subTitle }}</div>
                  </div>
                </template>

                <div
                  v-if="contentHtml"
                  class="markdown-body"
                  v-html="contentHtml"
                />
                <a-empty v-else-if="article.status === 'FAILED'" description="文章生成失败">
                  <template #description>
                    <span>生成失败：{{ article.errorMessage || '未知错误' }}</span>
                  </template>
                </a-empty>
                <a-empty v-else description="文章内容生成中，请稍后刷新" />
              </a-card>
            </a-col>
          </a-row>
        </template>

        <a-empty v-else-if="!loading" description="文章不存在或无权访问" />
      </a-spin>
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { getArticleDetail, type ArticleVO } from '@/api/article'
import { renderMarkdown } from '@/utils/markdown'

const route = useRoute()
const router = useRouter()

const article = ref<ArticleVO | null>(null)
const loading = ref(false)

const contentHtml = computed(() =>
  article.value?.fullContent
    ? renderMarkdown(article.value.fullContent)
    : article.value?.content
      ? renderMarkdown(article.value.content)
      : ''
)

const statusColor = computed(() => {
  const map: Record<string, string> = {
    PENDING: 'default',
    PROCESSING: 'processing',
    COMPLETED: 'success',
    FAILED: 'error',
  }
  return map[article.value?.status ?? ''] ?? 'default'
})

const statusText = computed(() => {
  const map: Record<string, string> = {
    PENDING: '排队中',
    PROCESSING: '生成中',
    COMPLETED: '已完成',
    FAILED: '失败',
  }
  return map[article.value?.status ?? ''] ?? ''
})

async function load() {
  loading.value = true
  try {
    const res = await getArticleDetail(route.params.taskId as string)
    article.value = res.data
  } catch {
    article.value = null
  } finally {
    loading.value = false
  }
}

function onExport() {
  if (!article.value?.fullContent) return
  const content = article.value.fullContent
  const filename = `${article.value.mainTitle || article.value.topic}.md`
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
  message.success('导出成功')
}

onMounted(load)
</script>

<style scoped>
.detail-page {
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
  padding: 24px;
}
.article-title {
  padding: 8px 0;
}
.main-title {
  font-size: 22px;
  font-weight: bold;
  line-height: 1.4;
}
.sub-title {
  font-size: 14px;
  color: #888;
  margin-top: 4px;
}

:deep(.markdown-body) h1,
:deep(.markdown-body) h2,
:deep(.markdown-body) h3 {
  font-weight: 600;
  margin: 16px 0 8px;
}
:deep(.markdown-body) h2 {
  font-size: 18px;
  border-bottom: 1px solid #eee;
  padding-bottom: 6px;
}
:deep(.markdown-body) p {
  margin: 8px 0;
  line-height: 1.8;
  color: #333;
}
:deep(.markdown-body) img {
  max-width: 100%;
  border-radius: 6px;
  margin: 12px 0;
  display: block;
}
</style>
