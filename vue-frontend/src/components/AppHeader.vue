<template>
  <a-layout-header class="app-header">
    <span class="logo" @click="router.push('/')">AI 爆款文章创作器</span>
    <a-space>
      <a-button type="link" style="color:#fff" @click="router.push('/article/list')">我的文章</a-button>
      <a-button
        v-if="userStore.isAdmin"
        type="link"
        style="color:#fff"
        @click="router.push('/admin/statistics')"
      >
        统计
      </a-button>
      <a-button
        v-if="!userStore.isVip"
        type="default"
        size="small"
        class="upgrade-btn"
        @click="router.push('/vip')"
      >
        升级 VIP
      </a-button>
      <a-tag v-else color="gold" class="vip-badge">VIP</a-tag>
      <a-dropdown>
        <a-space style="color:#fff;cursor:pointer">
          <a-avatar>{{ userStore.userInfo?.userName?.charAt(0) ?? 'U' }}</a-avatar>
          <span>{{ userStore.userInfo?.userName }}</span>
        </a-space>
        <template #overlay>
          <a-menu>
            <a-menu-item @click="router.push('/vip')">会员中心</a-menu-item>
            <a-menu-divider />
            <a-menu-item @click="onLogout">退出登录</a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </a-space>
  </a-layout-header>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { userLogout } from '@/api/user'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

async function onLogout() {
  await userLogout()
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #001529;
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo {
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  cursor: pointer;
}

.upgrade-btn {
  background: linear-gradient(135deg, #faad14, #fa8c16);
  border: none;
  color: #fff;
  font-weight: 600;
  border-radius: 4px;
}

.upgrade-btn:hover {
  opacity: 0.85;
}

.vip-badge {
  font-weight: 700;
  font-size: 13px;
}
</style>
