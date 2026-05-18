<template>
  <a-layout class="vip-page">
    <AppHeader />

    <a-layout-content class="vip-content">
      <div class="vip-container">
        <!-- 已是 VIP 的提示 -->
        <a-result
          v-if="userStore.isVip"
          status="success"
          title="您已是 VIP 会员"
          :sub-title="vipSince"
        >
          <template #extra>
            <a-button type="primary" @click="router.push('/')">开始创作</a-button>
          </template>
        </a-result>

        <!-- VIP 介绍 + 购买区 -->
        <template v-else>
          <div class="vip-hero">
            <h1 class="vip-title">升级 VIP 会员</h1>
            <p class="vip-subtitle">解锁全部 AI 创作能力，无限创作精彩内容</p>
          </div>

          <!-- 权益对比表 -->
          <a-card class="benefits-card" :bordered="false">
            <a-table
              :columns="columns"
              :data-source="benefits"
              :pagination="false"
              size="middle"
              row-key="feature"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'free'">
                  <a-tag v-if="record.free === true" color="green">✓</a-tag>
                  <a-tag v-else-if="record.free === false" color="default">✗</a-tag>
                  <span v-else>{{ record.free }}</span>
                </template>
                <template v-if="column.key === 'vip'">
                  <a-tag v-if="record.vip === true" color="gold">✓</a-tag>
                  <a-tag v-else-if="record.vip === false" color="default">✗</a-tag>
                  <span v-else>{{ record.vip }}</span>
                </template>
              </template>
            </a-table>
          </a-card>

          <!-- 价格 + 购买 -->
          <a-card class="price-card" :bordered="false">
            <div class="price-box">
              <div class="price-label">永久会员</div>
              <div class="price-amount">
                <span class="price-currency">$</span>
                <span class="price-num">199</span>
                <span class="price-unit">/永久</span>
              </div>
              <a-button
                type="primary"
                size="large"
                :loading="buying"
                class="buy-btn"
                @click="onBuy"
              >
                立即开通
              </a-button>
              <p class="price-note">支持 Visa / Mastercard / 支付宝</p>
            </div>
          </a-card>
        </template>

        <!-- 支付结果提示 -->
        <a-alert
          v-if="paymentResult === 'success'"
          class="payment-alert"
          type="success"
          message="支付成功！正在刷新会员状态..."
          show-icon
        />
        <a-alert
          v-if="paymentResult === 'cancel'"
          class="payment-alert"
          type="warning"
          message="支付已取消，如需开通请重新点击「立即开通」"
          show-icon
          closable
          @close="clearPaymentResult"
        />
      </div>
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import AppHeader from '@/components/AppHeader.vue'
import { useUserStore } from '@/stores/user'
import { createCheckout } from '@/api/payment'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const buying = ref(false)
const paymentResult = ref<'success' | 'cancel' | null>(null)

const vipSince = computed(() => {
  const t = userStore.userInfo?.vipTime
  return t ? `会员开通时间：${new Date(t).toLocaleDateString('zh-CN')}` : ''
})

const columns = [
  { title: '功能', dataIndex: 'feature', key: 'feature' },
  { title: '免费用户', dataIndex: 'free', key: 'free', align: 'center' as const },
  { title: 'VIP 会员', dataIndex: 'vip', key: 'vip', align: 'center' as const },
]

const benefits = [
  { feature: '文章创作数量', free: '最多 5 篇', vip: '无限制' },
  { feature: 'AI 图片生成（Nano Banana）', free: false, vip: true },
  { feature: 'AI 修改大纲', free: false, vip: true },
  { feature: '多种图片来源', free: true, vip: true },
  { feature: '多种文章风格', free: true, vip: true },
]

async function onBuy() {
  buying.value = true
  try {
    const res = await createCheckout('VIP_PERMANENT')
    window.location.href = res.data.checkoutUrl
  } catch (e: any) {
    message.error(e?.message || '创建支付失败，请重试')
  } finally {
    buying.value = false
  }
}

function clearPaymentResult() {
  paymentResult.value = null
  router.replace('/vip')
}

onMounted(async () => {
  const payment = route.query.payment as string
  if (payment === 'success') {
    paymentResult.value = 'success'
    // 刷新用户信息以获取最新 VIP 状态
    userStore.logout()
    await userStore.fetchLoginUser()
    if (userStore.isVip) {
      message.success('恭喜您成为 VIP 会员！')
    }
    router.replace('/vip')
  } else if (payment === 'cancel') {
    paymentResult.value = 'cancel'
  }
})
</script>

<style scoped>
.vip-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.vip-content {
  padding: 40px 24px;
}

.vip-container {
  max-width: 800px;
  margin: 0 auto;
}

.vip-hero {
  text-align: center;
  margin-bottom: 32px;
}

.vip-title {
  font-size: 32px;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 8px;
}

.vip-subtitle {
  font-size: 16px;
  color: #666;
}

.benefits-card {
  margin-bottom: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.price-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.price-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0;
}

.price-label {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  margin-bottom: 16px;
}

.price-amount {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 24px;
}

.price-currency {
  font-size: 24px;
  color: #faad14;
}

.price-num {
  font-size: 56px;
  font-weight: 700;
  color: #faad14;
  line-height: 1;
}

.price-unit {
  font-size: 16px;
  color: #999;
}

.buy-btn {
  width: 240px;
  height: 48px;
  font-size: 18px;
  border-radius: 24px;
  background: linear-gradient(135deg, #faad14, #fa8c16);
  border: none;
  margin-bottom: 12px;
}

.buy-btn:hover {
  background: linear-gradient(135deg, #ffc53d, #faad14);
}

.price-note {
  color: #999;
  font-size: 12px;
  margin: 0;
}

.payment-alert {
  margin-top: 24px;
}
</style>
