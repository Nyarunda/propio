# Propio Desk Role-Center Architecture

## Why the previous setup felt wrong
Frappe Desk behaves best when navigation is **module-first**, not workspace-first.

- Module-first: user clicks a module (like `Selling`), lands in one role center, sees focused sidebar.
- Workspace-first: user sees many unrelated workspaces in sidebar, which feels like clutter.

## Correct architecture (native Frappe pattern)
Use these layers together:

1. `Module Def` and `modules.txt`
2. Module landing workspace (role center)
3. User `module_profile` (module visibility)
4. User `default_workspace` (landing experience)
5. Workspace role assignments

## How Propio is structured
Modules:

- `Property`
- `Leasing`
- `Maintenance`
- `Finance`
- `Collections`
- `Owner`

DocTypes are now placed under module-native paths:

- `property/doctype/...`
- `leasing/doctype/...`
- `maintenance/doctype/...` (reserved for maintenance-native doctypes)
- `finance/doctype/...`
- `collections/doctype/...`
- `owner/doctype/...`

Reports are placed under module-native report paths:

- `collections/report/...`
- `owner/report/...`

## Role visibility model
For a clean Desk:

- assign `module_profile` on **User** (not Role)
- assign `default_workspace` on **User**
- limit each workspace using `roles`

This gives the behavior you wanted:

- a Leasing Officer logs in and sees Leasing-focused navigation
- an Accountant lands in Finance
- no generic ERP modules unless deliberately allowed

## Operations flow
Use the `Propio Operations` page buttons:

- `Audit Desk Structure`
- `Apply Desk Structure`

These call:

- `propio.api.desk_setup.audit_role_center_structure`
- `propio.api.desk_setup.apply_role_center_structure`

## Guardrails
- Do not remove compatibility modules from `modules.txt` until all doctypes are fully migrated.
- Avoid workspace content items that reference missing cards/charts.
- Use Frappe icon keys (for example `building-2`, `file-text`, `wrench`, `wallet`, `users`), not hard-coded emoji.
