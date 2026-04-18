from __future__ import unicode_literals

import json

import frappe
from frappe.utils import nowdate


def _upsert(doctype, name, payload):
    if frappe.db.exists(doctype, name):
        doc = frappe.get_doc(doctype, name)
        for k, v in payload.items():
            setattr(doc, k, v)
        doc.save(ignore_permissions=True)
    else:
        data = {"doctype": doctype, "name": name}
        data.update(payload)
        doc = frappe.get_doc(data)
        doc.insert(ignore_permissions=True)

    return name


@frappe.whitelist()
def get_occupancy_rate():
    total_units = frappe.db.count("Unit", {"status": "Active"})
    occupied_units = frappe.db.count("Unit", {"status": "Active", "occupancy_status": "Occupied"})
    if not total_units:
        return 0
    return round((occupied_units / total_units) * 100, 2)


@frappe.whitelist()
def get_collection_efficiency():
    from propio.api.payment_matching import calculate_collection_rate

    return calculate_collection_rate()


@frappe.whitelist()
def get_deposit_liability():
    # Lease-level deposit proxy until a dedicated Deposit Register exists.
    result = frappe.db.sql(
        """
        SELECT SUM(deposit_amount)
        FROM `tabLease`
        WHERE status IN ('Approved', 'Active', 'Expiring Soon')
        """,
    )
    return float((result[0][0] or 0) if result else 0)


@frappe.whitelist()
def get_fees_this_month():
    # If Management Fee Run is introduced later, this can be switched easily.
    # For now, expose active agreement count as a proxy metric.
    return frappe.db.count("Management Agreement", {"status": "Active"})


@frappe.whitelist()
def get_pending_payouts():
    result = frappe.db.sql(
        """
        SELECT SUM(payout_due)
        FROM `tabOwner Statement`
        WHERE status IN ('Approved', 'Reviewed')
        """,
    )
    return float((result[0][0] or 0) if result else 0)


@frappe.whitelist()
def ensure_number_cards_and_charts():
    cards = [
        ("Total Properties", "Property", "Document Type", "Count", "Property", json.dumps([["Property", "status", "=", "Active", False]])),
        ("Total Units", "Property", "Document Type", "Count", "Unit", json.dumps([["Unit", "status", "=", "Active", False]])),
        ("Occupied Units", "Property", "Document Type", "Count", "Unit", json.dumps([["Unit", "status", "=", "Active", False], ["Unit", "occupancy_status", "=", "Occupied", False]])),
        ("Vacant Units", "Property", "Document Type", "Count", "Unit", json.dumps([["Unit", "status", "=", "Active", False], ["Unit", "occupancy_status", "=", "Vacant", False]])),
        ("Occupancy Rate", "Property", "Custom", "Count", "Unit", "[]"),
        ("Active Leases", "Leasing", "Document Type", "Count", "Lease", json.dumps([["Lease", "status", "=", "Active", False]])),
        ("Expiring in 30 Days", "Leasing", "Document Type", "Count", "Lease", json.dumps([["Lease", "status", "=", "Active", False], ["Lease", "end_date", "Timespan", "next month", False]])),
        ("Pending Approvals", "Leasing", "Document Type", "Count", "Lease", json.dumps([["Lease", "approval_status", "=", "Pending Approval", False]])),
        ("Renewals Due", "Leasing", "Document Type", "Count", "Lease", json.dumps([["Lease", "status", "=", "Expiring Soon", False]])),
        ("Billed This Month", "Finance", "Document Type", "Sum", "Sales Invoice", json.dumps([["Sales Invoice", "posting_date", "Timespan", "this month", False], ["Sales Invoice", "docstatus", "=", 1, False]])),
        ("Outstanding Invoices", "Finance", "Document Type", "Sum", "Sales Invoice", json.dumps([["Sales Invoice", "outstanding_amount", ">", 0, False], ["Sales Invoice", "docstatus", "=", 1, False]])),
        ("Overdue Amount", "Finance", "Document Type", "Sum", "Sales Invoice", json.dumps([["Sales Invoice", "due_date", "<", nowdate(), False], ["Sales Invoice", "outstanding_amount", ">", 0, False], ["Sales Invoice", "docstatus", "=", 1, False]])),
        ("Deposit Liability", "Finance", "Custom", "Count", "Lease", "[]"),
        ("Collected This Month", "Collections", "Document Type", "Sum", "Payment Entry", json.dumps([["Payment Entry", "posting_date", "Timespan", "this month", False], ["Payment Entry", "docstatus", "=", 1, False], ["Payment Entry", "payment_type", "=", "Receive", False]])),
        ("Unmatched Payments", "Collections", "Document Type", "Count", "Payment Intake", json.dumps([["Payment Intake", "status", "=", "Unmatched", False]])),
        ("Collection Efficiency", "Collections", "Custom", "Count", "Sales Invoice", "[]"),
        ("Active Owners", "Owner", "Document Type", "Count", "Owner", json.dumps([["Owner", "status", "=", "Active", False]])),
        ("Active Agreements", "Owner", "Document Type", "Count", "Management Agreement", json.dumps([["Management Agreement", "status", "=", "Active", False]])),
        ("Fees This Month", "Owner", "Custom", "Count", "Management Agreement", "[]"),
        ("Pending Payouts", "Owner", "Custom", "Count", "Owner Statement", "[]"),
        ("Open Requests", "Propio", "Document Type", "Count", "Work Order", json.dumps([["Work Order", "status", "not in", ["Completed", "Closed", "Cancelled"], False]])),
        ("Open Work Orders", "Propio", "Document Type", "Count", "Work Order", json.dumps([["Work Order", "status", "not in", ["Completed", "Closed", "Cancelled"], False]])),
        ("Overdue SLAs", "Propio", "Document Type", "Count", "Work Order", json.dumps([["Work Order", "planned_end_date", "<", nowdate(), False], ["Work Order", "status", "not in", ["Completed", "Closed", "Cancelled"], False]])),
    ]

    methods = {
        "Occupancy Rate": "propio.api.kpi_setup.get_occupancy_rate",
        "Collection Efficiency": "propio.api.kpi_setup.get_collection_efficiency",
        "Deposit Liability": "propio.api.kpi_setup.get_deposit_liability",
        "Fees This Month": "propio.api.kpi_setup.get_fees_this_month",
        "Pending Payouts": "propio.api.kpi_setup.get_pending_payouts",
    }

    for name, module, card_type, fn, document_type, filters_json in cards:
        payload = {
            "label": name,
            "module": module,
            "is_public": 1,
            "type": card_type,
            "document_type": document_type,
            "function": fn,
            "filters_json": filters_json,
            "show_percentage_stats": 0,
        }
        if fn == "Sum":
            payload["aggregate_function_based_on"] = (
                "base_grand_total"
                if name == "Billed This Month"
                else "received_amount"
                if name == "Collected This Month"
                else "outstanding_amount"
            )
        if name in methods:
            payload["method"] = methods[name]

        _upsert("Number Card", name, payload)

    charts = [
        ("Property Status Distribution", "Property", "Property", "status", "Count", "", "Pie"),
        ("Unit Mix Analysis", "Property", "Unit", "unit_type", "Count", "", "Bar"),
        ("Occupancy Trend", "Property", "Unit", "modified", "Count", "", "Line"),
        ("Lease Expiry Trend", "Leasing", "Lease", "end_date", "Count", "", "Line"),
        ("Lease Status Distribution", "Leasing", "Lease", "status", "Count", "", "Donut"),
        ("Monthly Lease Revenue", "Leasing", "Lease Charge", "start_date", "Sum", "amount", "Bar"),
        ("Revenue Trend", "Finance", "Sales Invoice", "posting_date", "Sum", "base_grand_total", "Line"),
        ("Billing by Property", "Finance", "Sales Invoice", "company", "Sum", "base_grand_total", "Bar"),
        ("Collections Trend", "Collections", "Payment Entry", "posting_date", "Sum", "received_amount", "Line"),
        ("Payment Channel Distribution", "Collections", "Payment Intake", "payment_channel", "Sum", "amount", "Pie"),
        ("Arrears Aging", "Collections", "Sales Invoice", "due_date", "Sum", "outstanding_amount", "Bar"),
        ("Management Fee Trend", "Owner", "Management Agreement", "start_date", "Count", "", "Line"),
        ("Maintenance Aging", "Propio", "Work Order", "planned_end_date", "Count", "", "Bar"),
        ("SLA Performance", "Propio", "Work Order", "status", "Count", "", "Bar"),
    ]

    for chart_name, module, doctype, group_by, group_type, agg_field, chart_type in charts:
        payload = {
            "chart_name": chart_name,
            "chart_type": "Group By",
            "document_type": doctype,
            "group_by_based_on": group_by,
            "group_by_type": group_type,
            "type": chart_type,
            "module": module,
            "is_public": 1,
            "filters_json": "[]",
            "time_interval": "Monthly",
            "timespan": "Last Year",
        }
        if agg_field:
            payload["aggregate_function_based_on"] = agg_field
        _upsert("Dashboard Chart", chart_name, payload)

    frappe.db.commit()
    return {"number_cards": len(cards), "charts": len(charts)}
