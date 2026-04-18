<template>
  <section class="space-y-6">
    <div class="relative overflow-hidden rounded-2xl bg-gradient-to-r from-propio-600 to-propio-800 p-7 text-white shadow-lg">
      <h1 class="text-2xl font-bold tracking-tight">Welcome back, {{ dashboard?.tenant_name || 'Tenant' }}</h1>
      <p class="mt-1 text-propio-100">Lease, billing, and maintenance at a glance.</p>
      <div class="absolute -right-12 -top-12 h-36 w-36 rounded-full bg-white/10"></div>
      <div class="absolute -bottom-12 -left-12 h-28 w-28 rounded-full bg-white/10"></div>
    </div>

    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <KpiCard title="Monthly Rent" :value="fmtMoney(dashboard?.monthly_rent || 0)" />
      <KpiCard title="Outstanding Balance" :value="fmtMoney(dashboard?.outstanding_balance || 0)" />
      <KpiCard title="Next Due Date" :value="fmtDate(dashboard?.next_due_date)" />
      <KpiCard title="Lease End" :value="fmtDate(dashboard?.end_date)" />
    </div>

    <div class="grid gap-5 lg:grid-cols-2">
      <div class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-lg font-semibold">Recent Invoices</h2>
          <RouterLink to="/invoices" class="text-xs font-semibold text-propio-600 hover:underline">View all</RouterLink>
        </div>
        <div v-if="loading" class="space-y-2">
          <div v-for="i in 3" :key="i" class="skeleton h-14 rounded-lg"></div>
        </div>
        <div v-else-if="!invoices.length" class="py-8 text-sm text-slate-500">No invoices found.</div>
        <div v-else class="space-y-2">
          <div v-for="inv in invoices" :key="inv.name" class="hover-lift flex items-center justify-between rounded-xl bg-slate-50 p-3 dark:bg-slate-800/70">
            <div>
              <div class="text-sm font-semibold">{{ inv.name }}</div>
              <div class="text-xs text-slate-500">Due {{ fmtDate(inv.due_date) }}</div>
            </div>
            <div class="text-right">
              <div class="text-sm font-bold">{{ fmtMoney(inv.outstanding_amount || inv.grand_total || 0) }}</div>
              <div class="text-xs" :class="statusClass(inv.status)">{{ inv.status || 'Unpaid' }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-lg font-semibold">Maintenance</h2>
          <button class="rounded-lg bg-propio-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-propio-700" @click="showModal = true">
            + New Request
          </button>
        </div>
        <div v-if="loading" class="space-y-2">
          <div v-for="i in 3" :key="`m-${i}`" class="skeleton h-14 rounded-lg"></div>
        </div>
        <div v-else-if="!maintenance.length" class="py-8 text-sm text-slate-500">No requests yet.</div>
        <div v-else class="space-y-2">
          <div v-for="req in maintenance" :key="req.name" class="hover-lift flex items-center justify-between rounded-xl bg-slate-50 p-3 dark:bg-slate-800/70">
            <div>
              <div class="text-sm font-semibold">{{ req.subject || req.request_type || req.name }}</div>
              <div class="text-xs text-slate-500">{{ fmtDate(req.creation) }}</div>
            </div>
            <div class="text-xs font-semibold" :class="maintenanceClass(req.status)">{{ req.status || 'Open' }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <h2 class="mb-3 text-lg font-semibold">Lease Summary</h2>
      <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <div class="rounded-xl bg-slate-50 p-3 text-sm dark:bg-slate-800/70"><span class="text-slate-500">Property:</span> {{ dashboard?.property_name || '-' }}</div>
        <div class="rounded-xl bg-slate-50 p-3 text-sm dark:bg-slate-800/70"><span class="text-slate-500">Unit:</span> {{ dashboard?.unit_name || '-' }}</div>
        <div class="rounded-xl bg-slate-50 p-3 text-sm dark:bg-slate-800/70"><span class="text-slate-500">Billing Cycle:</span> {{ dashboard?.billing_cycle || '-' }}</div>
        <div class="rounded-xl bg-slate-50 p-3 text-sm dark:bg-slate-800/70"><span class="text-slate-500">Lease Start:</span> {{ fmtDate(dashboard?.start_date) }}</div>
        <div class="rounded-xl bg-slate-50 p-3 text-sm dark:bg-slate-800/70"><span class="text-slate-500">Lease End:</span> {{ fmtDate(dashboard?.end_date) }}</div>
        <div class="rounded-xl bg-slate-50 p-3 text-sm dark:bg-slate-800/70"><span class="text-slate-500">Deposit:</span> {{ fmtMoney(dashboard?.deposit_amount || 0) }}</div>
      </div>
    </div>

    <div v-if="showModal" class="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm" @click.self="showModal = false">
      <div class="w-full max-w-lg rounded-2xl bg-white p-5 shadow-2xl dark:bg-slate-900">
        <h3 class="mb-4 text-lg font-semibold">New Maintenance Request</h3>
        <div class="space-y-3">
          <div>
            <label class="mb-1 block text-xs font-semibold text-slate-500">Subject</label>
            <input v-model="newReq.subject" class="w-full rounded-lg border px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950" />
          </div>
          <div>
            <label class="mb-1 block text-xs font-semibold text-slate-500">Description</label>
            <textarea v-model="newReq.description" rows="4" class="w-full rounded-lg border px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"></textarea>
          </div>
          <div>
            <label class="mb-1 block text-xs font-semibold text-slate-500">Priority</label>
            <select v-model="newReq.priority" class="w-full rounded-lg border px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950">
              <option>Low</option>
              <option>Medium</option>
              <option>High</option>
              <option>Emergency</option>
            </select>
          </div>
        </div>
        <div class="mt-5 flex justify-end gap-2">
          <button class="rounded-lg border px-3 py-1.5 text-sm dark:border-slate-700" @click="showModal = false">Cancel</button>
          <button class="rounded-lg bg-propio-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-propio-700 disabled:opacity-60" :disabled="submitting" @click="submitReq">
            {{ submitting ? 'Submitting...' : 'Submit' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import dayjs from 'dayjs'
import { createMaintenanceRequest, fetchDashboard, fetchInvoices, fetchMaintenance } from '@/utils/api'
import { useToast } from '@/composables/useToast'
import KpiCard from '@/components/KpiCard.vue'

const loading = ref(true)
const submitting = ref(false)
const showModal = ref(false)
const dashboard = ref<any>(null)
const invoices = ref<any[]>([])
const maintenance = ref<any[]>([])
const newReq = ref({ subject: '', description: '', priority: 'Medium' })
const { push } = useToast()

const fmtMoney = (value: number) => `KES ${Number(value || 0).toLocaleString()}`
const fmtDate = (value?: string) => (value ? dayjs(value).format('DD MMM YYYY') : '-')

const statusClass = (status?: string) => {
  const s = (status || '').toLowerCase()
  if (s.includes('paid')) return 'text-emerald-600'
  if (s.includes('overdue')) return 'text-amber-600'
  if (s.includes('unpaid')) return 'text-rose-600'
  return 'text-slate-500'
}

const maintenanceClass = (status?: string) => {
  const s = (status || '').toLowerCase()
  if (s.includes('complete')) return 'text-emerald-600'
  if (s.includes('progress')) return 'text-sky-600'
  if (s.includes('pending')) return 'text-amber-600'
  return 'text-slate-500'
}

const loadAll = async () => {
  loading.value = true
  try {
    const [d, i, m] = await Promise.all([fetchDashboard(), fetchInvoices(5), fetchMaintenance(5)])
    dashboard.value = d
    invoices.value = i
    maintenance.value = m
  } catch {
    push({ title: 'Load failed', text: 'Could not load dashboard data.', type: 'error' })
  } finally {
    loading.value = false
  }
}

const submitReq = async () => {
  if (!newReq.value.subject || !newReq.value.description) {
    push({ title: 'Missing fields', text: 'Subject and description are required.', type: 'warning' })
    return
  }

  submitting.value = true
  try {
    await createMaintenanceRequest(newReq.value.subject, newReq.value.description, newReq.value.priority)
    push({ title: 'Request submitted', text: 'Maintenance team has been notified.', type: 'success' })
    showModal.value = false
    newReq.value = { subject: '', description: '', priority: 'Medium' }
    const m = await fetchMaintenance(5)
    maintenance.value = m
  } catch {
    push({ title: 'Submission failed', text: 'Please try again.', type: 'error' })
  } finally {
    submitting.value = false
  }
}

onMounted(loadAll)
</script>
