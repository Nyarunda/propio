<template>
  <div class="flex min-h-screen items-center justify-center bg-gradient-to-br from-propio-50 to-slate-100 px-4 py-12 dark:from-slate-950 dark:to-slate-900">
    <div class="w-full max-w-md">
      <div class="mb-6 text-center">
        <div class="mb-3 flex justify-center">
          <div class="flex h-14 w-14 items-center justify-center rounded-full bg-propio-100 dark:bg-propio-900/30">
            <svg class="h-7 w-7 text-propio-600 dark:text-propio-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
          </div>
        </div>
        <h1 class="text-3xl font-bold gradient-text">Propio</h1>
        <p class="mt-1 text-sm text-slate-600 dark:text-slate-300">Create New Password</p>
      </div>

      <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <h2 class="mb-2 text-center text-base font-semibold text-slate-900 dark:text-slate-100">Reset Password</h2>
        <p class="mb-4 text-center text-sm text-slate-600 dark:text-slate-400">Choose a new password for your account.</p>

        <form class="space-y-4" @submit.prevent="handleResetPassword">
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-200">New Password</label>
            <div class="relative mt-1">
              <input
                v-model="newPassword"
                :type="showNewPassword ? 'text' : 'password'"
                required
                :disabled="loading || !resetKey"
                class="w-full rounded-lg border border-slate-300 px-3 py-2 pr-10 text-sm outline-none focus:border-propio-500 focus:ring-1 focus:ring-propio-500 disabled:cursor-not-allowed disabled:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:disabled:bg-slate-900"
                placeholder="••••••••"
              />
              <button
                type="button"
                class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300"
                tabindex="-1"
                @click="showNewPassword = !showNewPassword"
              >
                <svg v-if="!showNewPassword" class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                </svg>
              </button>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-200">Confirm Password</label>
            <input
              v-model="confirmPassword"
              :type="showConfirmPassword ? 'text' : 'password'"
              required
              :disabled="loading || !resetKey"
              class="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-propio-500 focus:ring-1 focus:ring-propio-500 disabled:cursor-not-allowed disabled:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:disabled:bg-slate-900"
              placeholder="••••••••"
            />
          </div>

          <div v-if="newPassword" class="space-y-1">
            <div class="flex justify-between text-xs">
              <span class="text-slate-600 dark:text-slate-400">Password strength:</span>
              <span :class="strengthColor">{{ strengthText }}</span>
            </div>
            <div class="h-1 w-full rounded-full bg-slate-200 dark:bg-slate-700">
              <div class="h-1 rounded-full transition-all" :class="strengthBarClass" :style="{ width: strengthPercent }"></div>
            </div>
          </div>

          <button
            type="submit"
            :disabled="loading || !isFormValid"
            class="w-full rounded-lg bg-propio-600 py-2 text-sm font-semibold text-white transition hover:bg-propio-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span v-if="!loading">Reset Password</span>
            <span v-else class="flex items-center justify-center gap-2">
              <svg class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Resetting...
            </span>
          </button>

          <div class="text-center">
            <router-link to="/login" class="text-sm text-propio-600 hover:text-propio-700 dark:text-propio-400">
              ← Back to Login
            </router-link>
          </div>
        </form>

        <div
          v-if="message"
          class="mt-4 rounded-lg border p-3 text-sm"
          :class="messageType === 'error' ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-800 dark:bg-rose-950/50 dark:text-rose-200' : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200'"
        >
          {{ message }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const resetKey = computed(() => String(route.query.key || ''))
const newPassword = ref('')
const confirmPassword = ref('')
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)
const loading = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const hasMinLength = computed(() => newPassword.value.length >= 6)
const hasUpperCase = computed(() => /[A-Z]/.test(newPassword.value))
const hasLowerCase = computed(() => /[a-z]/.test(newPassword.value))
const hasNumber = computed(() => /[0-9]/.test(newPassword.value))

const strengthScore = computed(() => {
  let score = 0
  if (hasMinLength.value) score++
  if (hasUpperCase.value) score++
  if (hasLowerCase.value) score++
  if (hasNumber.value) score++
  return score
})

const strengthText = computed(() => {
  if (strengthScore.value <= 1) return 'Weak'
  if (strengthScore.value <= 2) return 'Fair'
  if (strengthScore.value <= 3) return 'Good'
  return 'Strong'
})

const strengthColor = computed(() => {
  if (strengthScore.value <= 1) return 'text-rose-600'
  if (strengthScore.value <= 2) return 'text-amber-600'
  if (strengthScore.value <= 3) return 'text-sky-600'
  return 'text-emerald-600'
})

const strengthBarClass = computed(() => {
  if (strengthScore.value <= 1) return 'bg-rose-600'
  if (strengthScore.value <= 2) return 'bg-amber-600'
  if (strengthScore.value <= 3) return 'bg-sky-600'
  return 'bg-emerald-600'
})

const strengthPercent = computed(() => `${(strengthScore.value / 4) * 100}%`)

const isFormValid = computed(
  () =>
    !!resetKey.value &&
    !!newPassword.value &&
    !!confirmPassword.value &&
    newPassword.value === confirmPassword.value &&
    hasMinLength.value
)

async function handleResetPassword() {
  loading.value = true
  message.value = ''
  try {
    const tokenRes = await axios.get('/api/method/propio.portal_utils.auth.get_csrf_token', { withCredentials: true })
    const csrfToken = tokenRes?.data?.message?.csrf_token || (window as any)?.frappe?.csrf_token || ''

    const { data } = await axios.post(
      '/api/method/propio.portal_utils.auth.reset_password',
      {
        key: resetKey.value,
        new_password: newPassword.value,
        confirm_password: confirmPassword.value,
        csrf_token: csrfToken,
      },
      {
        withCredentials: true,
        headers: { 'X-Frappe-CSRF-Token': csrfToken },
      }
    )
    const payload = data?.message || data
    if (payload?.success) {
      messageType.value = 'success'
      message.value = payload.message || 'Password reset successful. Redirecting to login...'
      window.setTimeout(() => {
        router.push('/login')
      }, 1500)
    } else {
      messageType.value = 'error'
      message.value = payload?.message || 'Failed to reset password.'
    }
  } catch (err: any) {
    if (err?.response?.status === 400 && err?.response?.data?.exc_type === 'CSRFTokenError') {
      messageType.value = 'error'
      message.value = 'Security token expired. Refreshing page...'
      window.setTimeout(() => window.location.reload(), 800)
      return
    }
    messageType.value = 'error'
    message.value = 'Could not reset password. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.gradient-text {
  background: linear-gradient(135deg, #1a4d8c 0%, #2d6a9f 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.dark .gradient-text {
  background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
</style>
