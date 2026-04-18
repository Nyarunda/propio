from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.permissions import add_permission, update_permission_property


# Only these modules should be visible to Propio operational users.
PROPIO_MODULES = ["Property", "Leasing", "Propio Maintenance", "Finance", "Collections", "Owner"]

# Modules to hide from Propio operational users.
BLOCKED_MODULES = [
    "Accounting",
    "Accounts",
    "Assets",
    "Buying",
    "CRM",
    "HR",
    "Manufacturing",
    "Projects",
    "Quality",
    "Selling",
    "Stock",
    "Subcontracting",
    "Support",
    "Website",
]

ROLE_POLICY = {
    "Property Manager": {
        "profile": "Propio - Property Manager",
        "workspace": "Portfolio",
    },
    "Portfolio Director": {
        "profile": "Propio - Property Manager",
        "workspace": "Portfolio",
    },
    "Leasing Officer": {
        "profile": "Propio - Leasing Officer",
        "workspace": "Leasing",
    },
    "Maintenance Coordinator": {
        "profile": "Propio - Maintenance Coordinator",
        "workspace": "Operations",
    },
    "Accountant": {
        "profile": "Propio - Finance",
        "workspace": "Billing",
    },
    "Collections Officer": {
        "profile": "Propio - Collections",
        "workspace": "Collections",
    },
    "Owner": {
        "profile": "Propio - Owner",
        "workspace": "Owners",
    },
}

LEGACY_WORKSPACES = [
    "Dashboard",
    "Build",
    "Home",
    "Accounting",
    "Selling",
    "Buying",
    "Stock",
    "Assets",
    "Property Hub",
    "Leasing Desk",
    "Maintenance Desk",
    "Finance Hub",
    "Collections Desk",
    "Owner Hub",
]


def _ensure_profile(profile_name):
    profile = frappe.get_doc("Module Profile", profile_name) if frappe.db.exists("Module Profile", profile_name) else None

    if not profile:
        profile = frappe.get_doc(
            {
                "doctype": "Module Profile",
                "module_profile": profile_name,
                "allow_all_modules": 0,
                "block_modules": [],
            }
        )

    profile.allow_all_modules = 0
    profile.block_modules = []

    for module_name in BLOCKED_MODULES:
        profile.append("block_modules", {"module": module_name})

    profile.save(ignore_permissions=True)
    return profile.name


def _get_users_for_role(role):
    rows = frappe.get_all("Has Role", filters={"role": role}, fields=["parent"])
    return sorted({row.parent for row in rows if row.parent and row.parent != "Guest"})


@frappe.whitelist()
def apply_role_center_structure(dry_run=0):
    """Apply module profile + default workspace policy by role.

    dry_run=1 will return the intended changes without writing.
    """
    dry_run = int(dry_run or 0)
    result = {
        "dry_run": bool(dry_run),
        "profiles": [],
        "user_updates": [],
        "workspace_hides": [],
        "notes": [],
    }

    profile_names = sorted({cfg["profile"] for cfg in ROLE_POLICY.values()})

    for profile_name in profile_names:
        if dry_run:
            result["profiles"].append({"profile": profile_name, "action": "would_upsert"})
        else:
            _ensure_profile(profile_name)
            result["profiles"].append({"profile": profile_name, "action": "upserted"})

    for role, cfg in ROLE_POLICY.items():
        users = _get_users_for_role(role)
        for user in users:
            update = {
                "user": user,
                "role": role,
                "module_profile": cfg["profile"],
                "default_workspace": cfg["workspace"],
            }
            result["user_updates"].append(update)

            if dry_run:
                continue

            if frappe.db.exists("User", user):
                frappe.db.set_value("User", user, "module_profile", cfg["profile"], update_modified=False)
                frappe.db.set_value("User", user, "default_workspace", cfg["workspace"], update_modified=False)

    for ws_name in LEGACY_WORKSPACES:
        if not frappe.db.exists("Workspace", ws_name):
            continue

        result["workspace_hides"].append({"workspace": ws_name, "action": "hide"})
        if dry_run:
            continue

        frappe.db.set_value("Workspace", ws_name, "is_hidden", 1, update_modified=False)

    if dry_run:
        result["notes"].append(_("Dry run only; no database changes committed."))
        return result

    frappe.db.commit()
    result["notes"].append(_("Role-center structure applied. Clear cache and reload Desk."))
    return result


@frappe.whitelist()
def audit_role_center_structure():
    """Return quick health snapshot of role-center setup."""
    missing_modules = [m for m in PROPIO_MODULES if not frappe.db.exists("Module Def", m)]
    existing_workspaces = frappe.get_all(
        "Workspace",
        filters={"name": ["in", list({cfg["workspace"] for cfg in ROLE_POLICY.values()})]},
        pluck="name",
    )
    missing_workspaces = sorted(set(cfg["workspace"] for cfg in ROLE_POLICY.values()) - set(existing_workspaces))

    users_missing_profile = []
    for role, cfg in ROLE_POLICY.items():
        for user in _get_users_for_role(role):
            module_profile = frappe.db.get_value("User", user, "module_profile")
            if module_profile != cfg["profile"]:
                users_missing_profile.append(
                    {
                        "user": user,
                        "role": role,
                        "expected_profile": cfg["profile"],
                        "actual_profile": module_profile,
                    }
                )

    return {
        "missing_modules": missing_modules,
        "missing_workspaces": missing_workspaces,
        "users_missing_profile": users_missing_profile,
    }


@frappe.whitelist()
def ensure_finance_insights_visibility():
    """
    Ensure Finance Hub users can read data sources used by KPI cards/charts.
    This grants read/report/export on Sales Invoice and Payment Entry to
    selected Propio finance roles via Custom DocPerm (non-destructive).
    """
    roles = ["Accountant", "Collections Officer", "Portfolio Director"]
    doctypes = ["Sales Invoice", "Payment Entry"]
    updated = []

    for doctype in doctypes:
        for role in roles:
            # Create a custom permission row if not present.
            add_permission(doctype, role, permlevel=0, ptype="read")
            # Explicitly set safe read-only analytics permissions.
            update_permission_property(doctype, role, 0, "read", 1, validate=False)
            update_permission_property(doctype, role, 0, "report", 1, validate=False)
            update_permission_property(doctype, role, 0, "export", 1, validate=False)
            updated.append({"doctype": doctype, "role": role})

    frappe.clear_cache()
    frappe.db.commit()
    return {"updated": updated, "count": len(updated)}


@frappe.whitelist()
def ensure_all_workspace_insights_visibility():
    """
    Ensure all role-center workspaces can read card/chart source doctypes.
    Grants read/report/export only (no write/create/delete changes).
    """
    # doctype -> roles that need analytics visibility
    visibility_map = {
        # Finance/Collections insights
        "Sales Invoice": ["Accountant", "Collections Officer", "Portfolio Director"],
        "Payment Entry": ["Accountant", "Collections Officer", "Portfolio Director"],
        # Maintenance insights
        "Work Order": ["Maintenance Coordinator", "Property Manager", "Portfolio Director"],
    }

    updated = []
    for doctype, roles in visibility_map.items():
        for role in roles:
            add_permission(doctype, role, permlevel=0, ptype="read")
            update_permission_property(doctype, role, 0, "read", 1, validate=False)
            update_permission_property(doctype, role, 0, "report", 1, validate=False)
            update_permission_property(doctype, role, 0, "export", 1, validate=False)
            updated.append({"doctype": doctype, "role": role})

    frappe.clear_cache()
    frappe.db.commit()
    return {"updated": updated, "count": len(updated)}
