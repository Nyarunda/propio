<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 text-slate-900 dark:from-slate-950 dark:to-slate-900 dark:text-slate-100">
    <header
      v-if="!isAuthPage"
      class="sticky top-0 z-30 border-b border-slate-200/80 bg-white/85 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80"
    >
      <div class="mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
        <div class="flex items-center gap-3">
          <div class="text-xl font-bold gradient-text">Propio</div>
          <div class="hidden text-xs text-slate-500 md:block">Tenant Portal</div>
        </div>

        <nav class="hidden gap-4 md:flex">
          <RouterLink
            v-for="item in nav"
            :key="item.to"
            :to="item.to"
            class="rounded-md px-2 py-1 text-sm font-medium transition"
            :class="$route.path === item.to ? 'bg-propio-100 text-propio-700 dark:bg-slate-800 dark:text-slate-100' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800'"
          >
            {{ item.label }}
          </RouterLink>
        </nav>

        <div class="flex items-center gap-2">
          <button class="rounded-md border px-2.5 py-1.5 text-xs hover-lift dark:border-slate-700" @click="toggleDarkMode">
            {{ isDark ? 'Light' : 'Dark' }}
          </button>
          <button class="rounded-md border px-2.5 py-1.5 text-xs hover-lift dark:border-slate-700" @click="openPaletteHint">
            Ctrl+K
          </button>
          <button class="rounded-md border px-2.5 py-1.5 text-xs hover-lift dark:border-slate-700" @click="onLogout">Logout</button>
        </div>
      </div>
    </header>

    <main :class="isAuthPage ? '' : 'mx-auto max-w-7xl p-4 md:p-6'">
      <RouterView v-slot="{ Component, route }">
        <Transition :name="(route.meta.transition as string) || 'fade'" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>

    <CommandPalette v-if="!isAuthPage" />
    <ToastStack />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { logout } from '@/utils/api'
import { useDarkMode } from '@/composables/useDarkMode'
import { useToast } from '@/composables/useToast'
import CommandPalette from '@/components/CommandPalette.vue'
import ToastStack from '@/components/ToastStack.vue'
import { useRoute } from 'vue-router'

const { isDark, toggleDarkMode } = useDarkMode()
const { push } = useToast()
const route = useRoute()
const isAuthPage = computed(() =>
  ['/login', '/forgot-password', '/reset-password'].includes(route.path)
)

const nav = [
  { label: 'Dashboard', to: '/' },
  { label: 'Leases', to: '/leases' },
  { label: 'Invoices', to: '/invoices' },
  { label: 'Payments', to: '/payments' },
  { label: 'Maintenance', to: '/maintenance' },
  { label: 'Profile', to: '/profile' }
]

function openPaletteHint() {
  push({ title: 'Command Palette', text: 'Press Ctrl+K to open quick navigation.', type: 'info' })
}

async function onLogout() {
  await logout()
  window.location.href = '/tenant-portal#/login'
}
</script>
