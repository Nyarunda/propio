from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import add_months, nowdate, get_first_day, get_last_day


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    return columns, data, None, chart


def get_columns():
    return [
        {"label": _("Period"), "fieldname": "period", "fieldtype": "Data", "width": 120},
        {"label": _("Billed Amount"), "fieldname": "billed", "fieldtype": "Currency", "width": 140},
        {"label": _("Collected Amount"), "fieldname": "collected", "fieldtype": "Currency", "width": 140},
        {"label": _("Collection Rate"), "fieldname": "rate", "fieldtype": "Percent", "width": 120},
        {"label": _("Target Rate"), "fieldname": "target", "fieldtype": "Percent", "width": 110},
        {"label": _("Variance"), "fieldname": "variance", "fieldtype": "Percent", "width": 100},
        {"label": _("Open Cases"), "fieldname": "open_cases", "fieldtype": "Int", "width": 100},
        {"label": _("Resolved Cases"), "fieldname": "resolved_cases", "fieldtype": "Int", "width": 120},
    ]


def get_data(filters):
    periods = []
    if filters.get("year"):
        year = int(filters.get("year"))
        periods = [f"{year}-{i:02d}" for i in range(1, 13)]
    else:
        for i in range(5, -1, -1):
            dt = getdate(add_months(nowdate(), -i))
            periods.append(dt.strftime("%Y-%m"))

    data = []
    for period in periods:
        year, month = period.split("-")
        month_i = int(month)

        billed = frappe.db.sql(
            """
            SELECT COALESCE(SUM(grand_total), 0)
            FROM `tabSales Invoice`
            WHERE YEAR(posting_date) = %s
              AND MONTH(posting_date) = %s
              AND docstatus = 1
            """,
            (int(year), month_i),
        )[0][0] or 0

        collected = frappe.db.sql(
            """
            SELECT COALESCE(SUM(paid_amount), 0)
            FROM `tabPayment Entry`
            WHERE YEAR(posting_date) = %s
              AND MONTH(posting_date) = %s
              AND docstatus = 1
              AND payment_type = 'Receive'
            """,
            (int(year), month_i),
        )[0][0] or 0

        period_start = get_first_day(f"{year}-{month}-01")
        period_end = get_last_day(f"{year}-{month}-01")

        open_cases = frappe.db.count(
            "Arrears Case",
            {
                "creation": ["between", [period_start, period_end]],
                "status": "Open",
            },
        ) if frappe.db.exists("DocType", "Arrears Case") else 0

        resolved_cases = frappe.db.count(
            "Arrears Case",
            {
                "resolution_date": ["between", [period_start, period_end]],
                "status": "Resolved",
            },
        ) if frappe.db.exists("DocType", "Arrears Case") else 0

        rate = (collected / billed * 100) if billed else 0
        target = 95

        data.append(
            {
                "period": f"{year}-{month}",
                "billed": billed,
                "collected": collected,
                "rate": round(rate, 2),
                "target": target,
                "variance": round(rate - target, 2),
                "open_cases": open_cases,
                "resolved_cases": resolved_cases,
            }
        )

    return data


def get_chart(data):
    if not data:
        return None

    return {
        "data": {
            "labels": [d["period"] for d in data],
            "datasets": [
                {"name": "Collection Rate", "values": [d["rate"] for d in data], "chart_type": "line"},
                {"name": "Target", "values": [d["target"] for d in data], "chart_type": "line"},
            ],
        },
        "type": "line",
        "height": 300,
        "colors": ["#2ecc71", "#e74c3c"],
    }
