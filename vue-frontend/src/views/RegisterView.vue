<template>
  <div class="auth-page">
    <a-card title="注册" class="auth-card">
      <a-form :model="form" layout="vertical" @finish="onFinish">
        <a-form-item label="账号" name="userAccount" :rules="[{ required: true, message: '请输入账号' }, { min: 4, message: '账号不能少于4位' }]">
          <a-input v-model:value="form.userAccount" placeholder="请输入账号" />
        </a-form-item>
        <a-form-item label="密码" name="userPassword" :rules="[{ required: true, message: '请输入密码' }, { min: 8, message: '密码不能少于8位' }]">
          <a-input-password v-model:value="form.userPassword" placeholder="请输入密码" />
        </a-form-item>
        <a-form-item label="确认密码" name="checkPassword" :rules="[{ required: true, message: '请确认密码' }, { validator: checkConfirm }]">
          <a-input-password v-model:value="form.checkPassword" placeholder="请再次输入密码" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="loading" block>注册</a-button>
        </a-form-item>
        <div class="auth-link">
          已有账号？<router-link to="/login">立即登录</router-link>
        </div>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { userRegister } from '@/api/user'

const router = useRouter()
const loading = ref(false)
const form = reactive({ userAccount: '', userPassword: '', checkPassword: '' })

function checkConfirm(_: unknown, value: string) {
  if (value && value !== form.userPassword) {
    return Promise.reject('两次密码不一致')
  }
  return Promise.resolve()
}

async function onFinish() {
  loading.value = true
  try {
    await userRegister(form)
    message.success('注册成功，请登录')
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
