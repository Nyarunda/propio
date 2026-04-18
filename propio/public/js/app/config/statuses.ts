export const PropertyStatus = {
  DRAFT: 'Draft',
  ACTIVE: 'Active',
  INACTIVE: 'Inactive',
  UNDER_MAINTENANCE: 'Under Maintenance',
  ARCHIVED: 'Archived',
} as const

export const UnitStatus = {
  DRAFT: 'Draft',
  AVAILABLE: 'Available',
  RESERVED: 'Reserved',
  OCCUPIED: 'Occupied',
  NOTICE_GIVEN: 'Notice Given',
  UNDER_MAINTENANCE: 'Under Maintenance',
  OFFLINE: 'Offline',
} as const

export const LeaseStatus = {
  DRAFT: 'Draft',
  PENDING_APPROVAL: 'Pending Approval',
  ACTIVE: 'Active',
  EXPIRING_SOON: 'Expiring Soon',
  RENEWED: 'Renewed',
  TERMINATED: 'Terminated',
  CLOSED: 'Closed',
} as const

export const ServiceRequestStatus = {
  OPEN: 'Open',
  ACKNOWLEDGED: 'Acknowledged',
  ASSIGNED: 'Assigned',
  IN_PROGRESS: 'In Progress',
  WAITING_PARTS: 'Waiting Parts',
  WAITING_VENDOR: 'Waiting Vendor',
  RESOLVED: 'Resolved',
  CLOSED: 'Closed',
  CANCELLED: 'Cancelled',
} as const

export const PaymentIntakeStatus = {
  DRAFT: 'Draft',
  RECEIVED: 'Received',
  MATCHED: 'Matched',
  PARTIALLY_MATCHED: 'Partially Matched',
  UNMATCHED: 'Unmatched',
  POSTED: 'Posted',
  REJECTED: 'Rejected',
} as const

export const ArrearsCaseStatus = {
  OPEN: 'Open',
  CONTACTED: 'Contacted',
  PROMISE_TO_PAY: 'Promise to Pay',
  PAYMENT_PLAN_ACTIVE: 'Payment Plan Active',
  ESCALATED: 'Escalated',
  DISPUTED: 'Disputed',
  SETTLED: 'Settled',
  CLOSED: 'Closed',
} as const

export const statusColors: Record<string, string> = {
  Draft: 'gray',
  Active: 'green',
  Inactive: 'red',
  'Under Maintenance': 'orange',
  'Pending Approval': 'yellow',
  'Expiring Soon': 'orange',
  Terminated: 'red',
  Closed: 'gray',
  Open: 'red',
  'In Progress': 'blue',
  Resolved: 'green',
  Unmatched: 'orange',
  Posted: 'green',
  Rejected: 'red',
}

export const priorityColors: Record<string, string> = {
  Low: 'gray',
  Medium: 'blue',
  High: 'orange',
  Urgent: 'red',
  Critical: 'purple',
}
