<template>
  <a-layout-header class="app-header">
    <span class="logo" @click="router.push('/')">{{ $t('home.title') }}</span>
    <a-space>
      <a-button type="link" style="color:#fff" @click="router.push('/article/list')">
        {{ $t('nav.articles') }}
      </a-button>
      <a-button
        v-if="userStore.isAdmin"
        type="link"
        style="color:#fff"
        @click="router.push('/admin/statistics')"
      >
        {{ $t('nav.stats') }}
      </a-button>
      <a-button
        v-if="!userStore.isVip"
        type="default"
        size="small"
        class="upgrade-btn"
        @click="router.push('/vip')"
      >
        {{ $t('nav.upgradeVip') }}
      </a-button>
      <a-tag v-else color="gold" class="vip-badge">VIP</a-tag>

      <!-- 语言切换 -->
      <div class="lang-switcher">
        <span
          :class="['lang-btn', { active: locale === 'zh' }]"
          @click="switchLang('zh')"
        >ZH</span>
        <span class="lang-sep">|</span>
        <span
          :class="['lang-btn', { active: locale === 'en' }]"
          @click="switchLang('en')"
        >EN</span>
      </div>

      <a-dropdown>
        <a-space style="color:#fff;cursor:pointer">
          <a-avatar>{{ userStore.userInfo?.userName?.charAt(0) ?? 'U' }}</a-avatar>
          <span>{{ userStore.userInfo?.userName }}</span>
        </a-space>
        <template #overlay>
          <a-menu>
            <a-menu-item @click="router.push('/vip')">{{ $t('nav.vip') }}</a-menu-item>
            <a-menu-divider />
            <a-menu-item @click="onLogout">{{ $t('nav.logout') }}</a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </a-space>
  </a-layout-header>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { userLogout } from '@/api/user'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const { locale } = useI18n()

function switchLang(lang: string) {
  locale.value = lang
  localStorage.setItem('lang', lang)
}

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

.lang-switcher {
  display: flex;
  align-items: center;
  gap: 2px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  padding: 2px 8px;
}

.lang-btn {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  padding: 0 2px;
  transition: color 0.2s;
  user-select: none;
}

.lang-btn:hover {
  color: #fff;
}

.lang-btn.active {
  color: #fff;
}

.lang-sep {
  color: rgba(255, 255, 255, 0.3);
  font-size: 11px;
}
</style>
