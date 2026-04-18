from __future__ import unicode_literals

import frappe


def _ensure_role(role_name, desk_access=0):
    if frappe.db.exists("Role", role_name):
        return
    role = frappe.get_doc(
        {
            "doctype": "Role",
            "role_name": role_name,
            "desk_access": int(desk_access),
        }
    )
    role.insert(ignore_permissions=True)


def execute():
    # If either doctype exists, keep existing maintenance model intact.
    if frappe.db.exists("DocType", "Maintenance Request") or frappe.db.exists("DocType", "Service Request"):
        return

    _ensure_role("Property Manager", desk_access=1)
    _ensure_role("Tenant Portal User", desk_access=0)

    doc = frappe.get_doc(
        {
            "doctype": "DocType",
            "name": "Maintenance Request",
            "module": "Propio",
            "custom": 1,
            "is_submittable": 0,
            "is_child_table": 0,
            "track_changes": 1,
            "track_seen": 1,
            "autoname": "hash",
            "title_field": "subject",
            "search_fields": "subject,status,priority",
            "fields": [
                {
                    "fieldname": "tenant",
                    "label": "Tenant",
                    "fieldtype": "Link",
                    "options": "Tenant",
                    "reqd": 1,
                    "in_list_view": 1,
                    "in_standard_filter": 1,
                },
                {
                    "fieldname": "lease",
                    "label": "Lease",
                    "fieldtype": "Link",
                    "options": "Lease",
                    "in_list_view": 1,
                },
                {
                    "fieldname": "property",
                    "label": "Property",
                    "fieldtype": "Link",
                    "options": "Property",
                    "in_list_view": 1,
                },
                {
                    "fieldname": "unit",
                    "label": "Unit",
                    "fieldtype": "Link",
                    "options": "Unit",
                    "in_list_view": 1,
                },
                {
                    "fieldname": "subject",
                    "label": "Subject",
                    "fieldtype": "Data",
                    "reqd": 1,
                    "in_list_view": 1,
                    "in_standard_filter": 1,
                },
                {
                    "fieldname": "description",
                    "label": "Description",
                    "fieldtype": "Text Editor",
                    "reqd": 1,
                },
                {
                    "fieldname": "priority",
                    "label": "Priority",
                    "fieldtype": "Select",
                    "options": "Low\nMedium\nHigh\nEmergency",
                    "default": "Medium",
                    "reqd": 1,
                    "in_list_view": 1,
                    "in_standard_filter": 1,
                },
                {
                    "fieldname": "status",
                    "label": "Status",
                    "fieldtype": "Select",
                    "options": "Open\nIn Progress\nCompleted\nCancelled",
                    "default": "Open",
                    "reqd": 1,
                    "in_list_view": 1,
                    "in_standard_filter": 1,
                },
                {
                    "fieldname": "category",
                    "label": "Category",
                    "fieldtype": "Select",
                    "options": "Plumbing\nElectrical\nHVAC\nStructural\nAppliance\nPest Control\nCleaning\nOther",
                },
                {"fieldname": "preferred_date", "label": "Preferred Date", "fieldtype": "Date"},
                {"fieldname": "preferred_time", "label": "Preferred Time", "fieldtype": "Time"},
                {"fieldname": "images", "label": "Images", "fieldtype": "Attach Image"},
                {
                    "fieldname": "assigned_to",
                    "label": "Assigned To",
                    "fieldtype": "Link",
                    "options": "User",
                },
                {
                    "fieldname": "resolution_notes",
                    "label": "Resolution Notes",
                    "fieldtype": "Text Editor",
                    "read_only": 1,
                },
                {
                    "fieldname": "resolved_date",
                    "label": "Resolved Date",
                    "fieldtype": "Datetime",
                    "read_only": 1,
                },
                {"fieldname": "cost_estimate", "label": "Cost Estimate", "fieldtype": "Currency"},
                {
                    "fieldname": "actual_cost",
                    "label": "Actual Cost",
                    "fieldtype": "Currency",
                    "read_only": 1,
                },
            ],
            "permissions": [
                {
                    "role": "System Manager",
                    "read": 1,
                    "write": 1,
                    "create": 1,
                    "delete": 1,
                    "report": 1,
                    "export": 1,
                    "email": 1,
                    "print": 1,
                    "share": 1,
                },
                {
                    "role": "Property Manager",
                    "read": 1,
                    "write": 1,
                    "create": 1,
                    "report": 1,
                    "export": 1,
                    "email": 1,
                    "print": 1,
                    "share": 1,
                },
                {
                    "role": "Tenant Portal User",
                    "read": 1,
                    "write": 1,
                    "create": 1,
                },
            ],
        }
    )
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
