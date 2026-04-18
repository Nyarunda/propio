<template>
  <section class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Maintenance Requests</h1>
      <button
        class="rounded-lg bg-propio-600 px-4 py-2 text-sm font-medium text-white hover:bg-propio-700"
        @click="showNewRequestModal = true"
      >
        + New Request
      </button>
    </div>

    <div class="flex flex-wrap gap-2">
      <button
        v-for="status in statuses"
        :key="status.label"
        class="rounded-full px-3 py-1 text-sm font-medium transition-colors"
        :class="currentStatus === status.value ? 'bg-propio-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200'"
        @click="currentStatus = status.value"
      >
        {{ status.label }}
      </button>
    </div>

    <div v-if="loading" class="py-8 text-center">
      <div class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-propio-600 border-t-transparent"></div>
    </div>

    <div v-else-if="requests.length === 0" class="rounded-xl bg-slate-50 py-12 text-center text-slate-500 dark:bg-slate-800/60">
      No maintenance requests found.
    </div>

    <div v-else class="space-y-4">
      <div
        v-for="request in requests"
        :key="request.name"
        class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md dark:border-slate-700 dark:bg-slate-900"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0 flex-1">
            <div class="mb-2 flex flex-wrap items-center gap-2">
              <h3 class="truncate text-base font-semibold text-slate-900 dark:text-white">{{ request.subject }}</h3>
              <span class="rounded-full px-2 py-0.5 text-xs font-medium" :class="statusClass(request.status)">
                {{ request.status || "Open" }}
              </span>
              <span class="rounded-full px-2 py-0.5 text-xs font-medium" :class="priorityClass(request.priority)">
                {{ request.priority || "Medium" }}
              </span>
            </div>
            <p class="line-clamp-2 text-sm text-slate-600 dark:text-slate-300">{{ request.description || "No description provided." }}</p>
            <div class="mt-2 flex flex-wrap gap-4 text-xs text-slate-500">
              <span>Submitted: {{ formatDate(request.creation) }}</span>
              <span v-if="request.preferred_date">Preferred: {{ formatDate(request.preferred_date) }}</span>
            </div>
          </div>
          <button
            v-if="request.status === 'Open'"
            class="text-sm text-rose-600 hover:text-rose-700"
            @click="cancelRequest(request.name)"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="showNewRequestModal"
      class="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      @click.self="showNewRequestModal = false"
    >
      <div class="w-full max-w-xl rounded-2xl bg-white shadow-xl dark:bg-slate-900">
        <div class="flex items-center justify-between border-b border-slate-200 p-4 dark:border-slate-700">
          <h3 class="text-lg font-semibold">New Maintenance Request</h3>
          <button class="text-slate-400 hover:text-slate-600" @click="showNewRequestModal = false">x</button>
        </div>

        <form class="space-y-4 p-4" @submit.prevent="submitRequest">
          <div>
            <label class="mb-1 block text-sm font-medium">Subject *</label>
            <input
              v-model="newRequest.subject"
              required
              class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-propio-500 focus:outline-none focus:ring-1 focus:ring-propio-500 dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium">Description *</label>
            <textarea
              v-model="newRequest.description"
              rows="4"
              required
              class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-propio-500 focus:outline-none focus:ring-1 focus:ring-propio-500 dark:border-slate-700 dark:bg-slate-800"
            ></textarea>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <div>
              <label class="mb-1 block text-sm font-medium">Priority</label>
              <select v-model="newRequest.priority" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800">
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Emergency">Emergency</option>
              </select>
            </div>
            <div>
              <label class="mb-1 block text-sm font-medium">Category</label>
              <select v-model="newRequest.category" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800">
                <option value="">Select category</option>
                <option value="Plumbing">Plumbing</option>
                <option value="Electrical">Electrical</option>
                <option value="HVAC">HVAC</option>
                <option value="Structural">Structural</option>
                <option value="Appliance">Appliance</option>
                <option value="Pest Control">Pest Control</option>
                <option value="Cleaning">Cleaning</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <div>
              <label class="mb-1 block text-sm font-medium">Preferred Date</label>
              <input v-model="newRequest.preferred_date" type="date" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800" />
            </div>
            <div>
              <label class="mb-1 block text-sm font-medium">Preferred Time</label>
              <input v-model="newRequest.preferred_time" type="time" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800" />
            </div>
          </div>

          <div class="flex justify-end gap-3 pt-2">
            <button
              type="button"
              class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
              @click="showNewRequestModal = false"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="submitting"
              class="rounded-lg bg-propio-600 px-4 py-2 text-sm font-medium text-white hover:bg-propio-700 disabled:opacity-60"
            >
              {{ submitting ? "Submitting..." : "Submit Request" }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { api } from '@/utils/api'
import { useToast } from '@/composables/useToast'

type MaintenanceRequest = {
  name: string
  subject: string
  description?: string
  status?: string
  priority?: string
  creation?: string
  preferred_date?: string
}

const { push } = useToast()
const loading = ref(false)
const submitting = ref(false)
const requests = ref<MaintenanceRequest[]>([])
const currentStatus = ref<string | null>(null)
const showNewRequestModal = ref(false)

const statuses = [
  { label: 'All', value: null },
  { label: 'Open', value: 'Open' },
  { label: 'In Progress', value: 'In Progress' },
  { label: 'Completed', value: 'Completed' },
  { label: 'Cancelled', value: 'Cancelled' },
]

const newRequest = ref({
  subject: '',
  description: '',
  priority: 'Medium',
  category: '',
  preferred_date: '',
  preferred_time: '',
})

const formatDate = (date?: string) => {
  if (!date) return '—'
  return dayjs(date).format('DD MMM YYYY')
}

const statusClass = (status?: string) => {
  const s = (status || '').toLowerCase()
  if (s === 'completed') return 'bg-emerald-100 text-emerald-700'
  if (s === 'in progress') return 'bg-sky-100 text-sky-700'
  if (s === 'open') return 'bg-amber-100 text-amber-700'
  if (s === 'cancelled') return 'bg-rose-100 text-rose-700'
  return 'bg-slate-100 text-slate-700'
}

const priorityClass = (priority?: string) => {
  const p = (priority || '').toLowerCase()
  if (p === 'emergency') return 'bg-rose-100 text-rose-700'
  if (p === 'high') return 'bg-orange-100 text-orange-700'
  if (p === 'medium') return 'bg-amber-100 text-amber-700'
  return 'bg-slate-100 text-slate-700'
}

const loadRequests = async () => {
  loading.value = true
  try {
    const params: Record<string, string | number> = { limit: 50 }
    if (currentStatus.value) params.status = currentStatus.value
    const { data } = await api.get('propio.portal_utils.tenant.get_maintenance_requests', { params })
    requests.value = (data?.message || []) as MaintenanceRequest[]
  } catch (_error) {
    push({ title: 'Load failed', text: 'Could not load maintenance requests.', type: 'error' })
  } finally {
    loading.value = false
  }
}

const submitRequest = async () => {
  if (!newRequest.value.subject || !newRequest.value.description) {
    push({ title: 'Missing fields', text: 'Please fill in all required fields.', type: 'warning' })
    return
  }
  submitting.value = true
  try {
    const { data } = await api.post('propio.portal_utils.tenant.submit_maintenance_request', newRequest.value)
    const result = data?.message || data
    if (!result?.success) {
      push({ title: 'Submission failed', text: result?.message || 'Failed to submit request.', type: 'error' })
      return
    }
    showNewRequestModal.value = false
    newRequest.value = { subject: '', description: '', priority: 'Medium', category: '', preferred_date: '', preferred_time: '' }
    await loadRequests()
    push({ title: 'Submitted', text: 'Maintenance request submitted successfully.', type: 'success' })
  } catch (_error) {
    push({ title: 'Submission failed', text: 'Failed to submit request.', type: 'error' })
  } finally {
    submitting.value = false
  }
}

const cancelRequest = async (requestName: string) => {
  try {
    const { data } = await api.post('propio.portal_utils.tenant.cancel_maintenance_request', {
      request_name: requestName,
    })
    const result = data?.message || data
    if (!result?.success) {
      push({ title: 'Cancel failed', text: result?.message || 'Unable to cancel request.', type: 'error' })
      return
    }
    await loadRequests()
    push({ title: 'Cancelled', text: 'Request cancelled successfully.', type: 'success' })
  } catch (_error) {
    push({ title: 'Cancel failed', text: 'Unable to cancel request.', type: 'error' })
  }
}

watch(currentStatus, () => {
  loadRequests()
})

onMounted(() => {
  loadRequests()
})
</script>
