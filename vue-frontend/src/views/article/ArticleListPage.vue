<template>
  <a-layout class="list-page">
    <AppHeader />

    <a-layout-content class="main">
      <a-card :title="t('article.list.title')" :bordered="false">
        <!-- 搜索栏 -->
        <a-row :gutter="16" style="margin-bottom:16px">
          <a-col :span="8">
            <a-input
              v-model:value="searchTopic"
              :placeholder="t('article.list.searchPlaceholder')"
              allow-clear
              @press-enter="loadList"
            />
          </a-col>
          <a-col :span="4">
            <a-select v-model:value="searchStatus" :placeholder="t('article.list.allStatus')" allow-clear style="width:100%">
              <a-select-option value="PENDING">{{ t('article.list.status.PENDING') }}</a-select-option>
              <a-select-option value="PROCESSING">{{ t('article.list.status.PROCESSING') }}</a-select-option>
              <a-select-option value="COMPLETED">{{ t('article.list.status.COMPLETED') }}</a-select-option>
              <a-select-option value="FAILED">{{ t('article.list.status.FAILED') }}</a-select-option>
            </a-select>
          </a-col>
          <a-col :span="4">
            <a-button type="primary" @click="loadList">{{ t('article.list.searchBtn') }}</a-button>
          </a-col>
        </a-row>

        <a-table
          :columns="columns"
          :data-source="articles"
          :loading="loading"
          :pagination="{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showTotal: (total: number) => t('article.list.total', { total }),
            onChange: onPageChange,
          }"
          row-key="taskId"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'topic'">
              <a-typography-paragraph :ellipsis="{ rows: 1, tooltip: record.topic }" style="margin:0">
                {{ record.topic }}
              </a-typography-paragraph>
            </template>

            <template v-if="column.key === 'mainTitle'">
              <span>{{ record.mainTitle || '—' }}</span>
            </template>

            <template v-if="column.key === 'status'">
              <a-tag :color="statusColor(record.status)">{{ t('article.list.status.' + record.status, record.status) }}</a-tag>
            </template>

            <template v-if="column.key === 'createTime'">
              {{ record.createTime?.slice(0, 16).replace('T', ' ') }}
            </template>

            <template v-if="column.key === 'action'">
              <a-space>
                <a-button
                  type="link"
                  size="small"
                  :disabled="record.status !== 'COMPLETED'"
                  @click="router.push(`/article/${record.taskId}`)"
                >
                  {{ t('article.list.viewBtn') }}
                </a-button>
                <a-popconfirm :title="t('article.list.deleteConfirm')" @confirm="onDelete(record)">
                  <a-button type="link" size="small" danger>{{ t('article.list.deleteBtn') }}</a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>
        </a-table>
      </a-card>
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useI18n } from 'vue-i18n'
import { listArticle, deleteArticle, type ArticleVO } from '@/api/article'
import AppHeader from '@/components/AppHeader.vue'

const { t } = useI18n()
const router = useRouter()

const articles = ref<ArticleVO[]>([])
const loading = ref(false)
const searchTopic = ref('')
const searchStatus = ref<string | undefined>(undefined)
const pagination = ref({ current: 1, pageSize: 10, total: 0 })

const columns = computed(() => [
  { title: t('article.list.columns.topic'), key: 'topic', dataIndex: 'topic', width: '25%' },
  { title: t('article.list.columns.mainTitle'), key: 'mainTitle', dataIndex: 'mainTitle', width: '25%' },
  { title: t('article.list.columns.status'), key: 'status', dataIndex: 'status', width: '10%' },
  { title: t('article.list.columns.createTime'), key: 'createTime', dataIndex: 'createTime', width: '18%' },
  { title: t('article.list.columns.action'), key: 'action', width: '12%' },
])

function statusColor(s: string) {
  const map: Record<string, string> = {
    PENDING: 'default',
    PROCESSING: 'processing',
    COMPLETED: 'success',
    FAILED: 'error',
  }
  return map[s] ?? 'default'
}

async function loadList() {
  loading.value = true
  try {
    const res = await listArticle({
      current: pagination.value.current,
      pageSize: pagination.value.pageSize,
      topic: searchTopic.value || undefined,
      status: searchStatus.value || undefined,
    })
    articles.value = res.data.records
    pagination.value.total = res.data.total
  } finally {
    loading.value = false
  }
}

function onPageChange(page: number, size: number) {
  pagination.value.current = page
  pagination.value.pageSize = size
  loadList()
}

async function onDelete(record: ArticleVO) {
  try {
    await deleteArticle(record.id)
    message.success(t('article.list.deleteSuccess'))
    loadList()
  } catch {
    // error already handled by interceptor
  }
}

onMounted(loadList)
</script>

<style scoped>
.list-page {
  min-height: 100vh;
  background: #f0f2f5;
}
.main {
  padding: 24px;
}
</style>
