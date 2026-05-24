<template>
  <a-layout class="stats-page">
    <a-layout-header class="header">
      <span class="logo" @click="router.push('/')">AI 爆款文章创作器</span>
      <a-space>
        <a-button type="link" style="color:#fff" @click="router.push('/')">创作</a-button>
        <a-button type="link" style="color:#fff" @click="router.push('/article/list')">我的文章</a-button>
      </a-space>
    </a-layout-header>

    <a-layout-content class="main">
      <div class="page-header">
        <h1 class="page-title">{{ t('stats.title') }}</h1>
        <a-button @click="loadData" :loading="loading">刷新数据</a-button>
      </div>

      <a-spin :spinning="loading" tip="加载中...">
        <!-- 4 张概览卡片 -->
        <a-row :gutter="16" style="margin-bottom:24px">
          <a-col :span="6">
            <a-card :bordered="false" class="stat-card">
              <a-statistic title="今日创作" :value="stats?.todayCount ?? 0" />
            </a-card>
          </a-col>
          <a-col :span="6">
            <a-card :bordered="false" class="stat-card">
              <a-statistic title="本周创作" :value="stats?.weekCount ?? 0" />
            </a-card>
          </a-col>
          <a-col :span="6">
            <a-card :bordered="false" class="stat-card">
              <a-statistic title="本月创作" :value="stats?.monthCount ?? 0" />
            </a-card>
          </a-col>
          <a-col :span="6">
            <a-card :bordered="false" class="stat-card">
              <a-statistic
                title="成功率"
                :value="stats?.successRate ?? 0"
                :precision="1"
                suffix="%"
              />
            </a-card>
          </a-col>
        </a-row>

        <!-- 图表区：创作趋势 + 性能统计 -->
        <a-row :gutter="16" style="margin-bottom:24px">
          <a-col :span="16">
            <a-card title="创作趋势" :bordered="false">
              <div ref="trendChartRef" style="height:280px" />
            </a-card>
          </a-col>
          <a-col :span="8">
            <a-card title="性能统计" :bordered="false" style="height:100%">
              <a-descriptions layout="vertical" :column="1">
                <a-descriptions-item label="平均创作耗时">
                  {{ formatDuration(stats?.avgDurationMs ?? 0) }}
                </a-descriptions-item>
                <a-descriptions-item label="总创作数">
                  {{ stats?.totalCount ?? 0 }} 篇
                </a-descriptions-item>
                <a-descriptions-item label="本周活跃用户">
                  {{ stats?.activeUserCount ?? 0 }} 人
                </a-descriptions-item>
              </a-descriptions>
            </a-card>
          </a-col>
        </a-row>

        <!-- 图表区：用户分析 + 配额使用 -->
        <a-row :gutter="16">
          <a-col :span="12">
            <a-card title="用户分析" :bordered="false">
              <div ref="userChartRef" style="height:280px" />
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card title="配额使用情况" :bordered="false">
              <div ref="quotaChartRef" style="height:280px" />
            </a-card>
          </a-col>
        </a-row>
      </a-spin>
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useI18n } from 'vue-i18n'
import * as echarts from 'echarts'
import { getStatisticsOverview, type StatisticsVO } from '@/api/statistics'

const { t } = useI18n()
const router = useRouter()
const loading = ref(false)
const stats = ref<StatisticsVO | null>(null)

// ECharts 实例（普通变量，不需要响应式）
const trendChartRef = ref<HTMLElement>()
const userChartRef = ref<HTMLElement>()
const quotaChartRef = ref<HTMLElement>()
let trendChart: echarts.ECharts | null = null
let userChart: echarts.ECharts | null = null
let quotaChart: echarts.ECharts | null = null

// ─── 数据加载 ─────────────────────────────────────────────────

async function loadData() {
  loading.value = true
  try {
    const res = await getStatisticsOverview()
    stats.value = res.data ?? null
    // 等 DOM 更新后渲染图表
    setTimeout(() => {
      renderTrendChart()
      renderUserChart()
      renderQuotaChart()
    }, 100)
  } catch (err) {
    message.error((err as Error).message || '加载统计数据失败')
  } finally {
    loading.value = false
  }
}

// ─── ECharts 渲染 ─────────────────────────────────────────────

function renderTrendChart() {
  if (!trendChartRef.value || !stats.value) return
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: ['今日', '本周', '本月', '总计'],
      axisLine: { lineStyle: { color: '#E2E8F0' } },
      axisLabel: { color: '#64748B' },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#F1F5F9' } },
      axisLabel: { color: '#64748B' },
    },
    series: [{
      name: '创作数量',
      type: 'bar',
      data: [
        stats.value.todayCount,
        stats.value.weekCount,
        stats.value.monthCount,
        stats.value.totalCount,
      ],
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#4ADE80' },
          { offset: 1, color: '#22C55E' },
        ]),
        borderRadius: [4, 4, 0, 0],
      },
      barWidth: '40%',
    }],
  })
}

function renderUserChart() {
  if (!userChartRef.value || !stats.value) return
  if (!userChart) userChart = echarts.init(userChartRef.value)
  const others = Math.max(
    0,
    stats.value.totalUserCount - stats.value.activeUserCount - stats.value.vipUserCount
  )
  userChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', right: '10%', top: 'center', textStyle: { color: '#64748B' } },
    series: [{
      name: '用户分布',
      type: 'pie',
      radius: ['40%', '70%'],
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
      data: [
        { value: stats.value.vipUserCount, name: 'VIP 会员', itemStyle: { color: '#22C55E' } },
        { value: stats.value.activeUserCount, name: '活跃用户', itemStyle: { color: '#3B82F6' } },
        { value: others, name: '其他用户', itemStyle: { color: '#94A3B8' } },
      ],
    }],
  })
}

function renderQuotaChart() {
  if (!quotaChartRef.value || !stats.value) return
  if (!quotaChart) quotaChart = echarts.init(quotaChartRef.value)
  const totalQuota = stats.value.totalUserCount * 5  // DEFAULT_QUOTA = 5
  const used = stats.value.quotaUsed
  const remaining = Math.max(0, totalQuota - used)
  quotaChart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      name: '配额统计',
      type: 'pie',
      radius: '70%',
      data: [
        { value: used, name: '已使用', itemStyle: { color: '#EF4444' } },
        { value: remaining, name: '剩余', itemStyle: { color: '#22C55E' } },
      ],
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' } },
      label: { formatter: '{b}: {c}' },
    }],
  })
}

// ─── 工具函数 ─────────────────────────────────────────────────

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

// ─── 窗口自适应 + 销毁 ────────────────────────────────────────

function handleResize() {
  trendChart?.resize()
  userChart?.resize()
  quotaChart?.resize()
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  userChart?.dispose()
  quotaChart?.dispose()
})
</script>

<style scoped>
.stats-page {
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
  font-weight: 700;
  cursor: pointer;
}
.main {
  padding: 24px;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
}
.stat-card {
  border-radius: 8px;
}
</style>
