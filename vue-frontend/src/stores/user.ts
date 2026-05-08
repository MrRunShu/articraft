import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { LoginUserVo } from '@/api/types.gen'
import { getLoginUser } from '@/api/user'

export const useUserStore = defineStore('user', () => {
  const userInfo = ref<LoginUserVo | null>(null)
  const hasFetched = ref(false)

  const isLogin = computed(() => userInfo.value !== null)
  const isAdmin = computed(() => userInfo.value?.userRole === 'admin')

  async function fetchLoginUser() {
    if (hasFetched.value) return
    hasFetched.value = true
    try {
      const res = await getLoginUser()
      userInfo.value = res.data
    } catch {
      userInfo.value = null
    }
  }

  function setUser(user: LoginUserVo) {
    userInfo.value = user
  }

  function clearUser() {
    userInfo.value = null
    hasFetched.value = false
  }

  return { userInfo, isLogin, isAdmin, fetchLoginUser, setUser, clearUser }
})
