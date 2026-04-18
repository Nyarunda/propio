<template>
  <div class="flex min-h-screen items-center justify-center bg-gradient-to-br from-propio-50 to-slate-100 px-4 py-12 dark:from-slate-950 dark:to-slate-900">
    <div class="w-full max-w-md">
      <!-- Logo/Brand -->
      <div class="mb-6 text-center">
        <div class="mb-3 flex justify-center">
          <div class="flex h-14 w-14 items-center justify-center rounded-full bg-propio-100 dark:bg-propio-900/30">
            <svg class="h-7 w-7 text-propio-600 dark:text-propio-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
          </div>
        </div>
        <h1 class="text-3xl font-bold gradient-text">Propio</h1>
        <p class="mt-1 text-sm text-slate-600 dark:text-slate-300">Tenant Portal</p>
      </div>

      <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <h2 class="mb-4 text-center text-base font-semibold text-slate-900 dark:text-slate-100">Sign In</h2>

        <form class="space-y-4" @submit.prevent="handleLogin">
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-200">Email Address</label>
            <div class="relative mt-1">
              <input
                v-model.trim="loginForm.email"
                type="email"
                required
                autocomplete="email"
                :disabled="busy"
                class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-propio-500 focus:ring-1 focus:ring-propio-500 disabled:cursor-not-allowed disabled:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:disabled:bg-slate-900"
                placeholder="tenant@example.com"
              />
              <div v-if="validationErrors.email" class="absolute -bottom-5 left-0 text-xs text-rose-500">
                {{ validationErrors.email }}
              </div>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-200">Password</label>
            <div class="relative mt-1">
              <input
                v-model="loginForm.password"
                :type="showPassword ? 'text' : 'password'"
                required
                autocomplete="current-password"
                :disabled="busy"
                class="w-full rounded-lg border border-slate-300 px-3 py-2 pr-10 text-sm outline-none focus:border-propio-500 focus:ring-1 focus:ring-propio-500 disabled:cursor-not-allowed disabled:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:disabled:bg-slate-900"
                placeholder="••••••••"
              />
              <button
                type="button"
                class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300"
                tabindex="-1"
                @click="showPassword = !showPassword"
              >
                <svg v-if="!showPassword" class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                </svg>
              </button>
            </div>
          </div>

          <button
            type="submit"
            :disabled="busy || !isFormValid"
            class="relative w-full rounded-lg bg-propio-600 py-2 text-sm font-semibold text-white transition hover:bg-propio-700 focus:outline-none focus:ring-2 focus:ring-propio-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span v-if="!busy">Sign In</span>
            <span v-else class="flex items-center justify-center gap-2">
              <svg class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Signing in...
            </span>
          </button>

          <div class="text-center">
            <router-link to="/forgot-password" class="text-xs text-propio-600 hover:underline dark:text-propio-400">
              Forgot password?
            </router-link>
          </div>
        </form>

        <div class="mt-4 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-700 dark:border-sky-900 dark:bg-sky-950/30 dark:text-sky-200">
          <div class="flex items-start gap-2">
            <svg class="mt-0.5 h-3 w-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>Account access is created by your property or lease manager. If you don't have login credentials, contact management.</span>
          </div>
        </div>

        <Transition
          enter-active-class="transition ease-out duration-200"
          enter-from-class="transform opacity-0 translate-y-2"
          enter-to-class="transform opacity-100 translate-y-0"
          leave-active-class="transition ease-in duration-150"
          leave-from-class="transform opacity-100 translate-y-0"
          leave-to-class="transform opacity-0 translate-y-2"
        >
          <div
            v-if="feedback.text"
            class="mt-3 rounded-lg border px-3 py-2 text-sm"
            :class="feedback.type === 'error' ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-800 dark:bg-rose-950/50 dark:text-rose-200' : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200'"
            role="alert"
          >
            <div class="flex items-start gap-2">
              <svg v-if="feedback.type === 'error'" class="mt-0.5 h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <svg v-else class="mt-0.5 h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{{ feedback.text }}</span>
              <button
                class="ml-auto text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300"
                aria-label="Dismiss"
                @click="feedback.text = ''"
              >
                <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, ref, watch } from 'vue'

const busy = ref(false)
const showPassword = ref(false)
const feedback = ref<{ type: 'error' | 'success'; text: string }>({ type: 'success', text: '' })
const validationErrors = ref({ email: '' })

const query = new URLSearchParams(window.location.search)

const loginForm = ref({
  email: query.get('email') || '',
  password: '',
})

const isFormValid = computed(() => {
  return loginForm.value.email.trim() !== "" && loginForm.value.password !== "" && !validationErrors.value.email
})

function validateEmail(email: string) {
  const emailRegex = /^[^\s@]+@([^\s@.,]+\.)+[^\s@.,]{2,}$/
  if (!email) {
    validationErrors.value.email = ""
    return true
  }
  if (!emailRegex.test(email)) {
    validationErrors.value.email = "Please enter a valid email address"
    return false
  }
  validationErrors.value.email = ""
  return true
}

function setError(text: string) {
  feedback.value = { type: 'error', text }
}

function setSuccess(text: string) {
  feedback.value = { type: "success", text }
}

async function handleLogin() {
  feedback.value.text = ''

  if (!validateEmail(loginForm.value.email)) {
    setError("Please enter a valid email address")
    return
  }
  if (!loginForm.value.email.trim()) {
    setError("Email is required")
    return
  }
  if (!loginForm.value.password) {
    setError("Password is required")
    return
  }

  busy.value = true
  try {
    // Use native Frappe login endpoint (stable auth/session flow).
    const formData = new URLSearchParams()
    formData.append('usr', loginForm.value.email.trim())
    formData.append('pwd', loginForm.value.password)
    const csrfToken = (window as any)?.frappe?.csrf_token
    if (csrfToken) formData.append('csrf_token', csrfToken)

    const loginResp = await fetch('/api/method/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      credentials: 'include',
      body: formData.toString(),
    })

    const loginData = await loginResp.json()
    if (!loginResp.ok || loginData?.message !== 'Logged In') {
      setError('Invalid email or password')
      loginForm.value.password = ''
      return
    }

    // Enforce portal eligibility after login.
    const { data } = await axios.get('/api/method/propio.portal_utils.auth.check_session', { withCredentials: true })
    const payload = data?.message || data
    if (!payload?.logged_in) {
      await axios.post('/api/method/propio.portal_utils.auth.portal_logout', {}, { withCredentials: true })
      setError('This account does not have tenant portal access. Please contact your property manager.')
      loginForm.value.password = ''
      return
    }

    setSuccess('Login successful! Redirecting...')
    window.setTimeout(() => {
      window.location.href = '/tenant-portal'
    }, 500)
  } catch (err: any) {
    if (err.code === "ECONNABORTED") {
      setError("Request timeout. Please check your connection and try again.")
    } else if (err?.response?.status === 400 && err?.response?.data?.exc_type === "CSRFTokenError") {
      setError("Security token expired. Refreshing page...")
      window.setTimeout(() => window.location.reload(), 800)
    } else if (err.response?.status === 403) {
      setError("Invalid email or password")
    } else if (err.response?.status === 500) {
      setError("Server error. Please try again later or contact support.")
    } else if (err.message === "Network Error") {
      setError("Network error. Please check your internet connection.")
    } else {
      setError(err?.response?.data?.message || "Login failed. Please try again.")
    }
    loginForm.value.password = ""
  } finally {
    busy.value = false
  }
}

watch(
  () => loginForm.value.email,
  (newEmail) => {
    validateEmail(newEmail)
    if (feedback.value.text) feedback.value.text = ""
  }
)

watch(
  () => loginForm.value.password,
  () => {
    if (feedback.value.text) feedback.value.text = ""
  }
)

onMounted(() => {
  const emailInput = document.querySelector('input[type="email"]') as HTMLInputElement | null
  if (emailInput && !loginForm.value.email) {
    emailInput.focus()
  }
})
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
