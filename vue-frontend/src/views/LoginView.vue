<template>
  <div class="auth-page">
    <a-card :title="t('auth.login')" class="auth-card">
      <a-form :model="form" :rules="rules" layout="vertical" @finish="onFinish">
        <a-form-item :label="t('auth.account')" name="userAccount">
          <a-input v-model:value="form.userAccount" :placeholder="t('auth.accountPlaceholder')" />
        </a-form-item>
        <a-form-item :label="t('auth.password')" name="userPassword">
          <a-input-password v-model:value="form.userPassword" :placeholder="t('auth.passwordPlaceholder')" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="loading" block>{{ t('auth.loginBtn') }}</a-button>
        </a-form-item>
        <div class="auth-link">
          {{ t('auth.noAccount') }}<router-link to="/register">{{ t('auth.register') }}</router-link>
        </div>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useI18n } from 'vue-i18n'
import { userLogin } from '@/api/user'
import { useUserStore } from '@/stores/user'

const { t } = useI18n()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const form = reactive({ userAccount: '', userPassword: '' })

const rules = computed(() => ({
  userAccount: [
    { required: true, message: t('auth.accountRequired') },
    { min: 4, message: t('auth.accountMinLength') }
  ],
  userPassword: [
    { required: true, message: t('auth.passwordRequired') },
    { min: 8, message: t('auth.passwordMinLength') }
  ]
}))

async function onFinish() {
  loading.value = true
  try {
    const res = await userLogin(form)
    userStore.setUser(res.data)
    message.success(t('auth.loginSuccess'))
    router.push('/')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
}
.auth-card {
  width: 400px;
}
.auth-link {
  text-align: center;
}
</style>
