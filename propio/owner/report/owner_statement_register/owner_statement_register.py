from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Statement No"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Owner Statement",
            "width": 140,
        },
        {"label": _("Owner"), "fieldname": "owner", "fieldtype": "Link", "options": "Owner", "width": 180},
        {
            "label": _("Property"),
            "fieldname": "property",
            "fieldtype": "Link",
            "options": "Property",
            "width": 180,
        },
        {"label": _("Period From"), "fieldname": "period_from", "fieldtype": "Date", "width": 100},
        {"label": _("Period To"), "fieldname": "period_to", "fieldtype": "Date", "width": 100},
        {"label": _("Rent Collected"), "fieldname": "rent_collected", "fieldtype": "Currency", "width": 140},
        {"label": _("Expenses"), "fieldname": "total_expenses", "fieldtype": "Currency", "width": 140},
        {"label": _("Management Fee"), "fieldname": "management_fee", "fieldtype": "Currency", "width": 140},
        {
            "label": _("NOI"),
            "fieldname": "net_operating_income",
            "fieldtype": "Currency",
            "width": 140,
        },
        {"label": _("Payout Due"), "fieldname": "payout_due", "fieldtype": "Currency", "width": 140},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
        {
            "label": _("Approved By"),
            "fieldname": "approved_by",
            "fieldtype": "Link",
            "options": "User",
            "width": 140,
        },
    ]


def get_data(filters):
    where_parts = ["1=1"]
    params = {}

    if filters.get("owner"):
        where_parts.append("owner = %(owner)s")
        params["owner"] = filters.get("owner")

    if filters.get("property"):
        where_parts.append("property = %(property)s")
        params["property"] = filters.get("property")

    if filters.get("status"):
        where_parts.append("status = %(status)s")
        params["status"] = filters.get("status")

    if filters.get("from_date"):
        where_parts.append("period_from >= %(from_date)s")
        params["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        where_parts.append("period_to <= %(to_date)s")
        params["to_date"] = filters.get("to_date")

    return frappe.db.sql(
        f"""
        SELECT
            name, owner, property, period_from, period_to,
            rent_collected, total_expenses, management_fee,
            net_operating_income, payout_due, status, approved_by
        FROM `tabOwner Statement`
        WHERE {' AND '.join(where_parts)}
        ORDER BY period_from DESC
        """,
        params,
        as_dict=True,
    )
