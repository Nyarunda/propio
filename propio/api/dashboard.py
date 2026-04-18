from __future__ import unicode_literals

import frappe
from frappe.utils import add_days, nowdate


def _doctype_exists(doctype_name: str) -> bool:
    return bool(frappe.db.exists("DocType", doctype_name))


def _safe_count(doctype_name, filters=None):
    if not _doctype_exists(doctype_name):
        return 0
    return frappe.db.count(doctype_name, filters or {})


@frappe.whitelist()
def get_manager_overview():
    return get_portfolio_summary()


@frappe.whitelist()
def get_portfolio_summary():
    return {
        "total_properties": _safe_count("Property", {"status": "Active"}),
        "total_units": _safe_count("Unit", {"status": "Active"}),
        "occupied_units": _safe_count("Unit", {"occupancy_status": "Occupied"}),
        "vacant_units": _safe_count("Unit", {"occupancy_status": "Vacant"}),
        "active_leases": _safe_count("Lease", {"status": "Active"}),
        "expiring_leases": get_expiring_leases_count(),
        "occupancy_rate": get_occupancy_rate(),
        "open_work_orders": _safe_count("Work Order", {"status": ["!=", "Closed"]}),
    }


@frappe.whitelist()
def get_expiring_leases_count():
    if not _doctype_exists("Lease"):
        return 0

    threshold = add_days(nowdate(), 30)
    return frappe.db.count(
        "Lease",
        {
            "status": "Active",
            "end_date": ["<=", threshold],
        },
    )


@frappe.whitelist()
def get_occupancy_rate():
    total_units = _safe_count("Unit", {"status": "Active"})
    occupied_units = _safe_count("Unit", {"occupancy_status": "Occupied"})

    if total_units == 0:
        return 0

    return round((occupied_units / total_units) * 100, 2)


@frappe.whitelist()
def get_revenue_summary():
    return {
        "monthly_billed": get_monthly_billed(),
        "monthly_collected": get_monthly_collected(),
        "outstanding": get_outstanding_receivables(),
        "collection_rate": get_collection_rate(),
    }


def get_monthly_billed():
    if not _doctype_exists("Sales Invoice"):
        return 0

    current_month_start = frappe.utils.get_first_day(nowdate())
    return (
        frappe.db.sql(
            """
            SELECT COALESCE(SUM(grand_total), 0)
            FROM `tabSales Invoice`
            WHERE posting_date >= %s
              AND docstatus = 1
            """,
            current_month_start,
        )[0][0]
        or 0
    )


def get_monthly_collected():
    if not _doctype_exists("Payment Entry"):
        return 0

    current_month_start = frappe.utils.get_first_day(nowdate())
    return (
        frappe.db.sql(
            """
            SELECT COALESCE(SUM(paid_amount), 0)
            FROM `tabPayment Entry`
            WHERE posting_date >= %s
              AND docstatus = 1
            """,
            current_month_start,
        )[0][0]
        or 0
    )


def get_outstanding_receivables():
    if not _doctype_exists("Sales Invoice"):
        return 0

    return (
        frappe.db.sql(
            """
            SELECT COALESCE(SUM(outstanding_amount), 0)
            FROM `tabSales Invoice`
            WHERE docstatus = 1
              AND outstanding_amount > 0
            """
        )[0][0]
        or 0
    )


def get_collection_rate():
    billed = get_monthly_billed()
    collected = get_monthly_collected()

    if billed == 0:
        return 0

    return round((collected / billed) * 100, 2)
