<template>
  <div class="auth-page">
    <a-card :title="t('auth.register')" class="auth-card">
      <a-form :model="form" :rules="rules" layout="vertical" @finish="onFinish">
        <a-form-item :label="t('auth.account')" name="userAccount">
          <a-input v-model:value="form.userAccount" :placeholder="t('auth.accountPlaceholder')" />
        </a-form-item>
        <a-form-item :label="t('auth.password')" name="userPassword">
          <a-input-password v-model:value="form.userPassword" :placeholder="t('auth.passwordPlaceholder')" />
        </a-form-item>
        <a-form-item :label="t('auth.confirmPassword')" name="checkPassword">
          <a-input-password v-model:value="form.checkPassword" :placeholder="t('auth.confirmPasswordPlaceholder')" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="loading" block>{{ t('auth.registerBtn') }}</a-button>
        </a-form-item>
        <div class="auth-link">
          {{ t('auth.hasAccount') }}<router-link to="/login">{{ t('auth.loginBtn') }}</router-link>
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
import { userRegister } from '@/api/user'

const { t } = useI18n()
const router = useRouter()
const loading = ref(false)
const form = reactive({ userAccount: '', userPassword: '', checkPassword: '' })

const rules = computed(() => ({
  userAccount: [
    { required: true, message: t('auth.accountRequired') },
    { min: 4, message: t('auth.accountMinLength') }
  ],
  userPassword: [
    { required: true, message: t('auth.passwordRequired') },
    { min: 8, message: t('auth.passwordMinLength') }
  ],
  checkPassword: [
    { required: true, message: t('auth.confirmPasswordRequired') },
    { validator: checkConfirm }
  ]
}))

function checkConfirm(_: unknown, value: string) {
  if (value && value !== form.userPassword) {
    return Promise.reject(t('auth.passwordMismatch'))
  }
  return Promise.resolve()
}

async function onFinish() {
  loading.value = true
  try {
    await userRegister(form)
    message.success(t('auth.registerSuccess'))
    router.push('/login')
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
