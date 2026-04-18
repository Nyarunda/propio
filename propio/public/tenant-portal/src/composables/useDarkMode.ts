import { ref, watch } from 'vue'

const getInitialDark = () => {
  if (typeof window === 'undefined') return false
  const saved = localStorage.getItem('tenant-portal-theme')
  if (saved === 'dark') return true
  if (saved === 'light') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

const isDark = ref(getInitialDark())

const applyTheme = (dark: boolean) => {
  if (typeof document === 'undefined') return
  document.documentElement.classList.toggle('dark', dark)
  localStorage.setItem('tenant-portal-theme', dark ? 'dark' : 'light')
}

watch(
  isDark,
  (value) => {
    applyTheme(value)
  },
  { immediate: true }
)

export function useDarkMode() {
  const toggleDarkMode = () => {
    isDark.value = !isDark.value
  }

  return { isDark, toggleDarkMode }
}
