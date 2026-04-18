export interface NavItem {
  id: string
  label: string
  icon: string
  to?: string
  doctype?: string
  report?: string
  children?: NavItem[]
  badge?: number | string
  badgeColor?: string
}

export const sidebarByRole: Record<string, NavItem[]> = {
  'Property Manager': [
    {
      id: 'overview',
      label: 'Overview',
      icon: 'home',
      to: '/app/property-hub',
    },
    {
      id: 'portfolio',
      label: 'Portfolio',
      icon: 'building-2',
      children: [
        { id: 'properties', label: 'Properties', icon: 'building-2', doctype: 'Property' },
        { id: 'units', label: 'Units', icon: 'grid-2x2', doctype: 'Unit' },
        { id: 'tenants', label: 'Tenants', icon: 'users', doctype: 'Tenant' },
        { id: 'owners', label: 'Owners', icon: 'briefcase', doctype: 'Owner' },
      ],
    },
    {
      id: 'tenancy',
      label: 'Tenancy',
      icon: 'file-text',
      children: [
        { id: 'leases', label: 'Leases', icon: 'file-text', doctype: 'Lease' },
        { id: 'renewals', label: 'Renewals', icon: 'refresh-cw', doctype: 'Lease Renewal' },
      ],
    },
    {
      id: 'maintenance',
      label: 'Maintenance',
      icon: 'wrench',
      doctype: 'Work Order',
      badge: 'pending',
      badgeColor: 'orange',
    },
    {
      id: 'collections',
      label: 'Collections',
      icon: 'badge-alert',
      doctype: 'Arrears Case',
      badge: '12',
      badgeColor: 'red',
    },
  ],

  'Leasing Officer': [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: 'home',
      to: '/app/leasing-desk',
    },
    {
      id: 'pipeline',
      label: 'Pipeline',
      icon: 'funnel',
      children: [
        { id: 'prospects', label: 'Prospects', icon: 'users', doctype: 'Prospect' },
        { id: 'viewings', label: 'Viewings', icon: 'calendar', doctype: 'Viewing' },
        { id: 'applications', label: 'Applications', icon: 'clipboard', doctype: 'Application' },
      ],
    },
    {
      id: 'listings',
      label: 'Listings',
      icon: 'layout-grid',
      doctype: 'Unit Listing',
    },
    {
      id: 'drafts',
      label: 'Lease Drafts',
      icon: 'file-pen',
      doctype: 'Lease',
      badge: '3',
      badgeColor: 'blue',
    },
  ],

  'Maintenance Coordinator': [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: 'home',
      to: '/app/maintenance-desk',
    },
    {
      id: 'requests',
      label: 'Service Requests',
      icon: 'message-square-warning',
      doctype: 'Service Request',
      badge: 'urgent',
      badgeColor: 'red',
    },
    {
      id: 'orders',
      label: 'Work Orders',
      icon: 'wrench',
      doctype: 'Work Order',
    },
    {
      id: 'preventive',
      label: 'Preventive',
      icon: 'shield-check',
      doctype: 'Preventive Schedule',
    },
    {
      id: 'vendors',
      label: 'Vendors',
      icon: 'briefcase-business',
      doctype: 'Vendor',
    },
  ],

  Accountant: [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: 'home',
      to: '/app/finance-hub',
    },
    {
      id: 'billing',
      label: 'Billing',
      icon: 'receipt',
      children: [
        { id: 'invoices', label: 'Invoices', icon: 'receipt-text', doctype: 'Rent Invoice' },
        { id: 'receipts', label: 'Receipts', icon: 'receipt', doctype: 'Rent Receipt' },
      ],
    },
    {
      id: 'payments',
      label: 'Payments',
      icon: 'wallet',
      doctype: 'Payment Intake',
      badge: 'unmatched',
      badgeColor: 'orange',
    },
    {
      id: 'reconciliation',
      label: 'Reconciliation',
      icon: 'scale',
      doctype: 'Reconciliation Batch',
    },
    {
      id: 'owner',
      label: 'Owner',
      icon: 'users',
      doctype: 'Owner Statement',
    },
  ],

  'Collections Officer': [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: 'home',
      to: '/app/collections-desk',
    },
    {
      id: 'arrears',
      label: 'Arrears Cases',
      icon: 'badge-alert',
      doctype: 'Arrears Case',
      badge: 'open',
      badgeColor: 'red',
    },
    {
      id: 'followups',
      label: "Today's Follow Ups",
      icon: 'phone-call',
      doctype: 'Collections Follow Up',
      badge: '5',
      badgeColor: 'orange',
    },
    {
      id: 'plans',
      label: 'Payment Plans',
      icon: 'list-todo',
      doctype: 'Payment Plan',
    },
    {
      id: 'disputes',
      label: 'Disputes',
      icon: 'shield-alert',
      doctype: 'Collections Dispute',
    },
  ],

  Owner: [
    {
      id: 'overview',
      label: 'Portfolio Overview',
      icon: 'home',
      to: '/app/owner-hub',
    },
    {
      id: 'properties',
      label: 'My Properties',
      icon: 'building-2',
      doctype: 'Property',
    },
    {
      id: 'statements',
      label: 'Statements',
      icon: 'file-bar-chart',
      doctype: 'Owner Statement',
    },
    {
      id: 'settlements',
      label: 'Settlements',
      icon: 'landmark',
      doctype: 'Settlement Run',
    },
  ],
}
