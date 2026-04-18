export interface AppRoute {
  path: string
  name: string
  page: string
  roles?: string[]
}

export const appDeskRoutes: AppRoute[] = [
  { path: '/app/property-hub', name: 'property-hub', page: 'manager_overview' },
  { path: '/app/leasing-desk', name: 'leasing-desk', page: 'leasing_pipeline' },
  { path: '/app/maintenance-desk', name: 'maintenance-desk', page: 'maintenance_board' },
  { path: '/app/finance-hub', name: 'finance-hub', page: 'finance_control' },
  { path: '/app/collections-desk', name: 'collections-desk', page: 'collections_desk' },
  { path: '/app/owner-hub', name: 'owner-hub', page: 'owner_portal' },
]
