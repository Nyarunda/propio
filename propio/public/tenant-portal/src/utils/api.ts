import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/method/',
  withCredentials: true,
  xsrfCookieName: 'csrf_token',
  xsrfHeaderName: 'X-Frappe-CSRF-Token',
})

api.interceptors.request.use((config) => {
  const csrf = (window as any)?.frappe?.csrf_token
  if (csrf) {
    config.headers = config.headers || {}
    ;(config.headers as any)['X-Frappe-CSRF-Token'] = csrf
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 403 && window.location.pathname.startsWith('/tenant-portal')) {
      window.location.href = '/tenant-portal#/login'
      return Promise.reject(error)
    }
    return Promise.reject(error)
  }
)

export type TenantDashboard = {
  tenant_name: string
  property_name: string
  unit_name: string
  lease_name: string
  start_date: string
  end_date: string
  billing_cycle: string
  deposit_amount: number
  monthly_rent: number
  outstanding_balance: number
  next_due_date: string
}

export async function fetchDashboard() {
  const { data } = await api.get('propio.api.tenant.get_active_lease')
  return (data && data.message) || null
}

export async function fetchInvoices(limit = 5) {
  const { data } = await api.get('propio.api.tenant.get_recent_invoices', { params: { limit } })
  return (data && data.message) || []
}

export async function fetchMaintenance(limit = 5) {
  const { data } = await api.get('propio.api.tenant.get_recent_maintenance', { params: { limit } })
  return (data && data.message) || []
}

export async function createMaintenanceRequest(subject: string, description: string, priority = 'Medium') {
  const { data } = await api.post('propio.api.tenant.create_maintenance_request', {
    subject,
    description,
    priority
  })
  return data?.message
}

export async function logout() {
  await api.post('propio.portal_utils.auth.portal_logout')
}
