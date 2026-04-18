<template>
  <div class="rounded-xl border bg-white p-4">
    <h1 class="text-xl font-semibold">Payments</h1>
    <p class="mt-2 text-slate-600">Payments can be processed through the existing portal payment flow.</p>
    <RouterLink class="mt-4 inline-block rounded bg-propio-600 px-4 py-2 text-white" to="/payments">Open Payment Page</RouterLink>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>
