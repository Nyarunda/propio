from __future__ import unicode_literals

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_months, getdate


def _doctype_exists(doctype_name: str) -> bool:
    return bool(frappe.db.exists("DocType", doctype_name))


def generate_billing_schedule(lease_name, lease=None):
    """Generate billing schedule documents for active billable charges."""
    if not _doctype_exists("Billing Schedule"):
        return

    if lease:
        if isinstance(lease, dict):
            lease = frappe._dict(lease)
        if hasattr(lease, "get"):
            lease_charges = lease.get("lease_charges") or []
            status = lease.get("status")
            lease_doc = lease
        else:
            lease_doc = frappe.get_doc("Lease", lease_name)
            lease_charges = lease_doc.get("lease_charges")
            status = lease_doc.status
    else:
        lease_doc = frappe.get_doc("Lease", lease_name)
        lease_charges = lease_doc.get("lease_charges")
        status = lease_doc.status

    if status != "Active":
        return

    active_charges = [c for c in lease_charges if c.get("billable")]
    for charge in active_charges:
        generate_charge_schedule(lease_doc, charge)


def generate_charge_schedule(lease, charge):
    start_date = getdate(charge.get("start_date") or lease.get("start_date"))
    end_date = getdate(charge.get("end_date") or lease.get("end_date"))
    current_date = start_date

    while current_date and end_date and current_date <= end_date:
        period_end = get_period_end(current_date, charge.get("frequency"))
        if period_end > end_date:
            period_end = end_date

        if not billing_schedule_exists(lease.get("name"), charge.get("charge_type"), current_date, period_end):
            create_billing_schedule(lease, charge, current_date, period_end)

        current_date = add_months(current_date, get_month_increment(charge.get("frequency")))


def get_period_end(start_date, frequency):
    if frequency == "Monthly":
        return add_months(start_date, 1) - timedelta(days=1)
    if frequency == "Quarterly":
        return add_months(start_date, 3) - timedelta(days=1)
    if frequency == "Annual":
        return add_months(start_date, 12) - timedelta(days=1)
    return start_date


def get_month_increment(frequency):
    if frequency == "Monthly":
        return 1
    if frequency == "Quarterly":
        return 3
    if frequency == "Annual":
        return 12
    return 1


def billing_schedule_exists(lease_name, charge_type, period_from, period_to):
    filters = {
        "lease": lease_name,
        "charge_period_from": period_from,
        "charge_period_to": period_to,
    }
    if charge_type and frappe.db.has_column("Billing Schedule", "charge_type"):
        filters["charge_type"] = charge_type
    return bool(frappe.db.exists("Billing Schedule", filters))


def create_billing_schedule(lease, charge, period_from, period_to):
    if not _doctype_exists("Billing Schedule"):
        return None

    billing_lines = []
    if _doctype_exists("Billing Line") or frappe.db.has_column("Billing Schedule", "billing_lines"):
        billing_lines = [
            {
                "charge_type": charge.get("charge_type"),
                "description": charge.get("description") or charge.get("charge_type"),
                "quantity": charge.get("quantity") or 1,
                "rate": charge.get("amount") or 0,
                "amount": (charge.get("amount") or 0) * (charge.get("quantity") or 1),
                "tax_template": charge.get("tax_template"),
                "income_account": charge.get("income_account"),
                "cost_center": charge.get("cost_center"),
            }
        ]

    doc_payload = {
        "doctype": "Billing Schedule",
        "lease": lease.get("name"),
        "tenant": lease.get("tenant"),
        "property": lease.get("property"),
        "company": lease.get("company"),
        "currency": lease.get("currency"),
        "charge_period_from": period_from,
        "charge_period_to": period_to,
        "due_date": period_to + timedelta(days=14),
        "source_type": "Lease Charge",
        "billing_status": "Draft",
    }

    if billing_lines:
        doc_payload["billing_lines"] = billing_lines

    schedule = frappe.get_doc(doc_payload)
    schedule.insert(ignore_permissions=True)
    return schedule.name


def mark_schedule_ready(schedule_name):
    schedule = frappe.get_doc("Billing Schedule", schedule_name)
    if schedule.billing_status == "Draft":
        schedule.billing_status = "Ready"
        schedule.save()


def create_invoice_from_schedule(schedule_name):
    schedule = frappe.get_doc("Billing Schedule", schedule_name)

    if schedule.billing_status != "Ready":
        frappe.throw(_("Billing schedule is not ready for invoicing."))

    if not _doctype_exists("Sales Invoice"):
        frappe.throw(_("Sales Invoice DocType is required."))

    customer = frappe.get_value("Tenant", schedule.tenant, "customer")
    if not customer:
        frappe.throw(_("Tenant {0} must be linked to a Customer.").format(schedule.tenant))

    invoice = frappe.get_doc(
        {
            "doctype": "Sales Invoice",
            "customer": customer,
            "company": schedule.company,
            "currency": schedule.currency,
            "posting_date": getdate(),
            "due_date": schedule.due_date,
            "items": [],
        }
    )

    for line in schedule.get("billing_lines") or []:
        invoice.append(
            "items",
            {
                "item_code": f"RENT-{line.charge_type}",
                "item_name": line.description,
                "qty": line.quantity,
                "rate": line.rate,
                "amount": line.amount,
                "income_account": line.income_account,
                "cost_center": line.cost_center,
            },
        )

    invoice.insert()
    invoice.submit()

    if frappe.db.has_column("Billing Schedule", "sales_invoice"):
        schedule.sales_invoice = invoice.name
    schedule.billing_status = "Invoiced"
    schedule.save()

    return invoice.name
