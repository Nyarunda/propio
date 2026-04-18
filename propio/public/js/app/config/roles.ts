export type AppRole =
  | 'Property Manager'
  | 'Leasing Officer'
  | 'Maintenance Coordinator'
  | 'Accountant'
  | 'Collections Officer'
  | 'Owner'
  | 'Portfolio Director'
  | 'System Manager'
  | 'Administrator'

export interface RoleProfile {
  name: string
  roles: AppRole[]
  workspaces: string[]
}

export const roleProfiles: Record<string, RoleProfile> = {
  'Property Operations Profile': {
    name: 'Property Operations Profile',
    roles: ['Property Manager', 'Maintenance Coordinator'],
    workspaces: ['Property Hub', 'Maintenance Desk'],
  },
  'Leasing Profile': {
    name: 'Leasing Profile',
    roles: ['Leasing Officer'],
    workspaces: ['Leasing Desk'],
  },
  'Finance Profile': {
    name: 'Finance Profile',
    roles: ['Accountant', 'Collections Officer'],
    workspaces: ['Finance Hub', 'Collections Desk'],
  },
  'Owner Portal Profile': {
    name: 'Owner Portal Profile',
    roles: ['Owner'],
    workspaces: ['Owner Hub'],
  },
  'Executive Profile': {
    name: 'Executive Profile',
    roles: ['Portfolio Director'],
    workspaces: ['Property Hub', 'Reports'],
  },
}

export const defaultWorkspaceByRole: Record<AppRole, string> = {
  'Property Manager': 'Property Hub',
  'Leasing Officer': 'Leasing Desk',
  'Maintenance Coordinator': 'Maintenance Desk',
  Accountant: 'Finance Hub',
  'Collections Officer': 'Collections Desk',
  Owner: 'Owner Hub',
  'Portfolio Director': 'Property Hub',
  'System Manager': 'Administration',
  Administrator: 'Administration',
}
