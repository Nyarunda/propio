<template>
  <div class="pointer-events-none fixed bottom-4 right-4 z-50 space-y-2">
    <div
      v-for="toast in toasts"
      :key="toast.id"
      class="pointer-events-auto flex w-80 items-start justify-between rounded-xl border bg-white/95 p-3 shadow-lg backdrop-blur dark:border-slate-700 dark:bg-slate-900/95"
    >
      <div class="mr-3">
        <p class="text-sm font-semibold" :class="titleClass(toast.type)">{{ toast.title }}</p>
        <p v-if="toast.text" class="mt-1 text-xs text-slate-600 dark:text-slate-300">{{ toast.text }}</p>
      </div>
      <button class="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200" @click="remove(toast.id)">x</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useToast, type ToastType } from '@/composables/useToast'

const { toasts, remove } = useToast()

const titleClass = (type: ToastType) => {
  if (type === 'success') return 'text-emerald-600'
  if (type === 'error') return 'text-rose-600'
  if (type === 'warning') return 'text-amber-600'
  return 'text-sky-600'
}
</script>
