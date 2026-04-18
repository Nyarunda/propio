from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import nowdate


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Tenant"), "fieldname": "tenant", "fieldtype": "Link", "options": "Tenant", "width": 180},
        {"label": _("Property"), "fieldname": "property", "fieldtype": "Link", "options": "Property", "width": 180},
        {"label": _("Unit"), "fieldname": "unit", "fieldtype": "Link", "options": "Unit", "width": 120},
        {"label": _("Lease"), "fieldname": "lease", "fieldtype": "Link", "options": "Lease", "width": 140},
        {"label": _("Invoice"), "fieldname": "invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
        {"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
        {"label": _("Days Overdue"), "fieldname": "days_overdue", "fieldtype": "Int", "width": 110},
        {"label": _("Outstanding"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 120},
        {"label": _("0-30 Days"), "fieldname": "range_0_30", "fieldtype": "Currency", "width": 120},
        {"label": _("31-60 Days"), "fieldname": "range_31_60", "fieldtype": "Currency", "width": 120},
        {"label": _("61-90 Days"), "fieldname": "range_61_90", "fieldtype": "Currency", "width": 120},
        {"label": _("90+ Days"), "fieldname": "range_90_plus", "fieldtype": "Currency", "width": 120},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
    ]


def get_data(filters):
    si_has_lease = frappe.db.has_column("Sales Invoice", "lease")
    si_has_property = frappe.db.has_column("Sales Invoice", "property")
    si_has_tenant = frappe.db.has_column("Sales Invoice", "tenant")

    select_parts = [
        "si.name AS invoice",
        "si.customer AS customer",
        "si.due_date AS due_date",
        "si.outstanding_amount AS outstanding_amount",
        "DATEDIFF(CURDATE(), si.due_date) AS days_overdue",
    ]
    if si_has_lease:
        select_parts.append("si.lease AS lease")
    else:
        select_parts.append("NULL AS lease")
    if si_has_property:
        select_parts.append("si.property AS property")
    else:
        select_parts.append("NULL AS property")
    if si_has_tenant:
        select_parts.append("si.tenant AS tenant")
    else:
        select_parts.append("NULL AS tenant")

    where_parts = ["si.docstatus = 1", "si.outstanding_amount > 0"]
    params = {}

    if filters.get("days_overdue_min") is not None:
        where_parts.append("DATEDIFF(CURDATE(), si.due_date) >= %(days_overdue_min)s")
        params["days_overdue_min"] = int(filters.get("days_overdue_min"))

    if filters.get("days_overdue_max") is not None:
        where_parts.append("DATEDIFF(CURDATE(), si.due_date) <= %(days_overdue_max)s")
        params["days_overdue_max"] = int(filters.get("days_overdue_max"))

    if filters.get("property") and si_has_property:
        where_parts.append("si.property = %(property)s")
        params["property"] = filters.get("property")

    if filters.get("tenant") and si_has_tenant:
        where_parts.append("si.tenant = %(tenant)s")
        params["tenant"] = filters.get("tenant")

    rows = frappe.db.sql(
        f"""
        SELECT {", ".join(select_parts)}
        FROM `tabSales Invoice` si
        WHERE {' AND '.join(where_parts)}
        ORDER BY si.due_date ASC
        """,
        params,
        as_dict=True,
    )

    data = []
    for row in rows:
        days = row.days_overdue if (row.days_overdue or 0) > 0 else 0

        lease = row.get("lease")
        tenant = row.get("tenant")
        property_name = row.get("property")

        if lease:
            if not tenant:
                tenant = frappe.db.get_value("Lease", lease, "tenant")
            if not property_name:
                property_name = frappe.db.get_value("Lease", lease, "property")

        if not tenant and row.get("customer") and frappe.db.exists("DocType", "Tenant"):
            tenant = frappe.db.get_value("Tenant", {"customer": row.get("customer")}, "name")

        unit = None
        if lease and frappe.db.exists("DocType", "Lease Unit"):
            unit = frappe.db.get_value("Lease Unit", {"parent": lease}, "unit")

        report_row = {
            "tenant": tenant,
            "property": property_name,
            "unit": unit,
            "lease": lease,
            "invoice": row.invoice,
            "due_date": row.due_date,
            "days_overdue": days,
            "outstanding": row.outstanding_amount,
            "range_0_30": row.outstanding_amount if 0 < days <= 30 else 0,
            "range_31_60": row.outstanding_amount if 31 <= days <= 60 else 0,
            "range_61_90": row.outstanding_amount if 61 <= days <= 90 else 0,
            "range_90_plus": row.outstanding_amount if days > 90 else 0,
            "status": get_status(days),
        }

        if filters.get("property") and report_row.get("property") != filters.get("property"):
            continue
        if filters.get("tenant") and report_row.get("tenant") != filters.get("tenant"):
            continue

        data.append(report_row)

    if data:
        data.append(
            {
                "tenant": _("Total"),
                "outstanding": sum(d["outstanding"] for d in data),
                "range_0_30": sum(d["range_0_30"] for d in data),
                "range_31_60": sum(d["range_31_60"] for d in data),
                "range_61_90": sum(d["range_61_90"] for d in data),
                "range_90_plus": sum(d["range_90_plus"] for d in data),
            }
        )

    return data


def get_status(days):
    if days <= 0:
        return "Current"
    if days <= 30:
        return "1-30 Days"
    if days <= 60:
        return "31-60 Days"
    if days <= 90:
        return "61-90 Days"
    return "90+ Days"
