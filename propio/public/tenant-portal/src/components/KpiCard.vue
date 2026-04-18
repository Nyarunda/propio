<template>
  <div class="hover-lift rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
    <div class="text-[11px] uppercase tracking-wide text-slate-500">{{ title }}</div>
    <div class="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">{{ value }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; value: string }>()
</script>
