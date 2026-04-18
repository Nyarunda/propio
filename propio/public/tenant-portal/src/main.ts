import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import { createPinia } from 'pinia'
import axios from 'axios'
import App from './App.vue'
import './style.css'

// Ensure Frappe CSRF cookie is attached as expected header on all axios POST/PUT/PATCH/DELETE calls.
axios.defaults.withCredentials = true
axios.defaults.xsrfCookieName = 'csrf_token'
axios.defaults.xsrfHeaderName = 'X-Frappe-CSRF-Token'

axios.interceptors.request.use((config) => {
  const csrf = (window as any)?.frappe?.csrf_token
  if (csrf) {
    config.headers = config.headers || {}
    ;(config.headers as any)['X-Frappe-CSRF-Token'] = csrf
  }
  return config
})

const routes = [
  { path: '/', component: () => import('./views/Dashboard.vue'), meta: { title: 'Dashboard', transition: 'fade', requiresAuth: true } },
  { path: '/leases', component: () => import('./views/Leases.vue'), meta: { title: 'My Lease', transition: 'slide', requiresAuth: true } },
  { path: '/invoices', component: () => import('./views/Invoices.vue'), meta: { title: 'Invoices', transition: 'slide', requiresAuth: true } },
  { path: '/payments', component: () => import('./views/Payments.vue'), meta: { title: 'Payments', transition: 'slide', requiresAuth: true } },
  { path: '/maintenance', component: () => import('./views/Maintenance.vue'), meta: { title: 'Maintenance', transition: 'slide', requiresAuth: true } },
  { path: '/profile', component: () => import('./views/Profile.vue'), meta: { title: 'Profile', transition: 'slide', requiresAuth: true } },
  { path: '/login', component: () => import('./views/Login.vue'), meta: { title: 'Login', transition: 'fade', public: true } },
  { path: '/forgot-password', component: () => import('./views/ForgotPassword.vue'), meta: { title: 'Forgot Password', transition: 'fade', public: true } },
  { path: '/reset-password', component: () => import('./views/ResetPassword.vue'), meta: { title: 'Reset Password', transition: 'fade', public: true } },
]

const router = createRouter({
  history: createWebHashHistory('/tenant-portal/'),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  }
})

let authCache: null | { logged_in: boolean; user_type?: string } = null

async function getPortalAuthState(force = false) {
  if (!force && authCache) return authCache
  try {
    const { data } = await axios.get('/api/method/propio.portal_utils.auth.get_current_user')
    const message = data?.message || {}
    authCache = {
      logged_in: !!message.logged_in && message.user_type === 'tenant',
      user_type: message.user_type,
    }
  } catch (_err) {
    authCache = { logged_in: false }
  }
  return authCache
}

router.beforeEach(async (to, _from, next) => {
  document.title = `${(to.meta.title as string) || 'Tenant Portal'} | Propio`

  const auth = await getPortalAuthState()
  if (to.meta.public) {
    // Keep /login as a redirect target for already-authenticated users.
    if (to.path === '/login' && auth.logged_in) return next('/')
    return next()
  }

  if (to.path === '/login') {
    if (auth.logged_in) return next('/')
    return next()
  }

  if (to.meta.requiresAuth && !auth.logged_in) {
    return next('/login')
  }

  return next()
})

createApp(App).use(createPinia()).use(router).mount('#app')
