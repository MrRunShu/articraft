<template>
  <a-layout class="list-page">
    <a-layout-header class="header">
      <span class="logo">AI 爆款文章创作器</span>
      <a-space>
        <a-button type="primary" @click="router.push('/')">创作新文章</a-button>
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
      <a-card title="我的文章" :bordered="false">
        <!-- 搜索栏 -->
        <a-row :gutter="16" style="margin-bottom:16px">
          <a-col :span="8">
            <a-input
              v-model:value="searchTopic"
              placeholder="搜索选题关键词"
              allow-clear
              @press-enter="loadList"
            />
          </a-col>
          <a-col :span="4">
            <a-select v-model:value="searchStatus" placeholder="全部状态" allow-clear style="width:100%">
              <a-select-option value="PENDING">排队中</a-select-option>
              <a-select-option value="PROCESSING">生成中</a-select-option>
              <a-select-option value="COMPLETED">已完成</a-select-option>
              <a-select-option value="FAILED">失败</a-select-option>
            </a-select>
          </a-col>
          <a-col :span="4">
            <a-button type="primary" @click="loadList">搜索</a-button>
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
            showTotal: (total: number) => `共 ${total} 篇`,
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
              <a-tag :color="statusColor(record.status)">{{ statusText(record.status) }}</a-tag>
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
                  查看
                </a-button>
                <a-popconfirm title="确定删除这篇文章吗？" @confirm="onDelete(record)">
                  <a-button type="link" size="small" danger>删除</a-button>
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { listArticle, deleteArticle, type ArticleVO } from '@/api/article'
import { useUserStore } from '@/stores/user'
import { userLogout } from '@/api/user'

const router = useRouter()
const userStore = useUserStore()

const articles = ref<ArticleVO[]>([])
const loading = ref(false)
const searchTopic = ref('')
const searchStatus = ref<string | undefined>(undefined)
const pagination = ref({ current: 1, pageSize: 10, total: 0 })

const columns = [
  { title: '选题', key: 'topic', dataIndex: 'topic', width: '25%' },
  { title: '标题', key: 'mainTitle', dataIndex: 'mainTitle', width: '25%' },
  { title: '状态', key: 'status', dataIndex: 'status', width: '10%' },
  { title: '创建时间', key: 'createTime', dataIndex: 'createTime', width: '18%' },
  { title: '操作', key: 'action', width: '12%' },
]

function statusColor(s: string) {
  const map: Record<string, string> = {
    PENDING: 'default',
    PROCESSING: 'processing',
    COMPLETED: 'success',
    FAILED: 'error',
  }
  return map[s] ?? 'default'
}

function statusText(s: string) {
  const map: Record<string, string> = {
    PENDING: '排队中',
    PROCESSING: '生成中',
    COMPLETED: '已完成',
    FAILED: '失败',
  }
  return map[s] ?? s
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
    message.success('删除成功')
    loadList()
  } catch {
    // error already handled by interceptor
  }
}

async function onLogout() {
  await userLogout()
  userStore.logout()
  message.success('已退出登录')
  router.push('/login')
}

onMounted(loadList)
</script>

<style scoped>
.list-page {
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
</style>
