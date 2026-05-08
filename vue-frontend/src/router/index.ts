import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { guest: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { guest: true },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

// 路由守卫：未登录跳登录页，已登录不能再访问登录/注册页
router.beforeEach(async (to) => {
  const userStore = useUserStore()

  if (!userStore.isLogin) {
    await userStore.fetchLoginUser()
  }

  if (to.meta.requiresAuth && !userStore.isLogin) {
    return { name: 'login' }
  }

  if (to.meta.guest && userStore.isLogin) {
    return { name: 'home' }
  }
})

export default router
