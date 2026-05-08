<template>
  <div class="home-page">
    <a-layout>
      <a-layout-header class="header">
        <span class="logo">AI 爆款文章创作器</span>
        <div class="user-info">
          <a-dropdown>
            <a-space>
              <a-avatar :src="userStore.userInfo?.userAvatar">
                {{ userStore.userInfo?.userName?.charAt(0) ?? 'U' }}
              </a-avatar>
              <span>{{ userStore.userInfo?.userName ?? userStore.userInfo?.userAccount }}</span>
            </a-space>
            <template #overlay>
              <a-menu>
                <a-menu-item key="logout" @click="onLogout">退出登录</a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-layout-header>
      <a-layout-content class="content">
        <a-result status="success" title="登录成功！" sub-title="欢迎使用 AI 爆款文章创作器。" />
      </a-layout-content>
    </a-layout>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { userLogout } from '@/api/user'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

async function onLogout() {
  await userLogout()
  userStore.clearUser()
  message.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #001529;
  padding: 0 24px;
}
.logo {
  color: white;
  font-size: 18px;
  font-weight: bold;
}
.user-info {
  color: white;
  cursor: pointer;
}
.content {
  padding: 48px;
}
</style>
