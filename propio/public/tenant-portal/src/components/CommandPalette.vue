<template>
  <div v-if="open" class="fixed inset-0 z-40 flex items-start justify-center bg-black/40 p-4 pt-24 backdrop-blur-sm" @click.self="close">
    <div class="w-full max-w-xl overflow-hidden rounded-2xl border bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900">
      <div class="flex items-center gap-2 border-b px-4 py-3 dark:border-slate-700">
        <span class="text-slate-400">/</span>
        <input
          v-model="query"
          class="w-full bg-transparent text-sm outline-none"
          placeholder="Search pages..."
          @keydown.esc="close"
          @keydown.enter="runFirst"
        />
      </div>
      <div class="max-h-80 overflow-auto py-2">
        <button
          v-for="item in filtered"
          :key="item.to"
          class="flex w-full items-start gap-2 px-4 py-2 text-left hover:bg-slate-100 dark:hover:bg-slate-800"
          @click="go(item.to)"
        >
          <span class="text-sm font-medium">{{ item.label }}</span>
          <span class="text-xs text-slate-500">{{ item.description }}</span>
        </button>
        <div v-if="!filtered.length" class="px-4 py-6 text-sm text-slate-500">No command found.</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const open = ref(false)
const query = ref('')

const items = [
  { label: 'Dashboard', to: '/', description: 'Overview and KPIs' },
  { label: 'My Lease', to: '/leases', description: 'Lease details' },
  { label: 'Invoices', to: '/invoices', description: 'Billing statements' },
  { label: 'Payments', to: '/payments', description: 'Payment history' },
  { label: 'Maintenance', to: '/maintenance', description: 'Requests and status' },
  { label: 'Profile', to: '/profile', description: 'User account' }
]

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return items
  return items.filter((item) => item.label.toLowerCase().includes(q) || item.description.toLowerCase().includes(q))
})

const go = (to: string) => {
  router.push(to)
  close()
}

const runFirst = () => {
  if (filtered.value.length) go(filtered.value[0].to)
}

const close = () => {
  open.value = false
  query.value = ''
}

const onKey = (e: KeyboardEvent) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    open.value = !open.value
  }
  if (e.key === 'Escape') close()
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>
