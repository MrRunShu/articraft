import axios from 'axios'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import router from '@/router'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000,
  withCredentials: true,
})

request.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data.code === 0) {
      return data
    }
    // 未登录：仅在非被动检查时才跳转，避免路由守卫死循环
    if (data.code === 40100) {
      const userStore = useUserStore()
      userStore.clearUser()
      // 只有当前不在登录页时才跳转并提示
      if (router.currentRoute.value.name !== 'login') {
        message.warning('请先登录')
        router.push('/login')
      }
      return Promise.reject(new Error(data.message))
    }
    message.error(data.message || '请求失败')
    return Promise.reject(new Error(data.message))
  },
  (error) => {
    message.error(error.message || '网络错误')
    return Promise.reject(error)
  },
)

export default request
