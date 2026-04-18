from __future__ import unicode_literals

import frappe
from frappe.utils import now_datetime

from propio.portal_utils.auth import get_tenant_for_user


def _has(doctype_name, fieldname):
    return frappe.get_meta(doctype_name).has_field(fieldname)


def _status_options(doctype_name, fieldname):
    field = frappe.get_meta(doctype_name).get_field(fieldname)
    if not field or not getattr(field, "options", None):
        return []
    return [opt.strip() for opt in field.options.split("\n") if opt and opt.strip()]


def _default_payment_intake_status():
    """Pick a safe initial status that won't violate configured workflows."""
    doctype_name = "Payment Intake"
    status_field = "status"
    if not _has(doctype_name, status_field):
        return None

    options = _status_options(doctype_name, status_field)
    if not options:
        return None

    workflow = frappe.db.get_value(
        "Workflow",
        {"document_type": doctype_name, "is_active": 1},
        ["name", "workflow_state_field"],
        as_dict=True,
    )
    if workflow and (workflow.get("workflow_state_field") or status_field) == status_field:
        if "Draft" in options:
            return "Draft"
        # Let framework defaults handle it if Draft is not an available state.
        return None

    # No active workflow on status field: use operational default.
    if "Received" in options:
        return "Received"
    return options[0]


@frappe.whitelist()
def process_payment(invoice, amount, method, phone=None):
    tenant = get_tenant_for_user(frappe.session.user)
    if not tenant:
        return {"success": False, "message": "Tenant not found"}

    customer = frappe.db.get_value("Tenant", tenant, "customer") if frappe.db.has_column("Tenant", "customer") else None
    invoice_customer = frappe.db.get_value("Sales Invoice", invoice, "customer")
    if customer and invoice_customer != customer:
        return {"success": False, "message": "Invalid invoice"}

    company = frappe.db.get_value("Sales Invoice", invoice, "company")
    currency = frappe.db.get_value("Sales Invoice", invoice, "currency") or "KES"

    payment_data = {
        "doctype": "Payment Intake",
        "payment_reference": f"PORTAL-{frappe.generate_hash(length=8)}",
        "tenant": tenant,
        "company": company,
        "payment_channel": method,
        "currency": currency,
        "amount": amount,
        "payment_date": now_datetime(),
        "raw_reference": invoice,
    }

    initial_status = _default_payment_intake_status()
    if initial_status:
        payment_data["status"] = initial_status

    if phone and _has("Payment Intake", "mpesa_code") and method == "M-Pesa":
        payment_data["mpesa_code"] = phone

    payment = frappe.get_doc(payment_data)
    payment.insert(ignore_permissions=True)

    try:
        from propio.api.payment_matching import auto_match_payment

        auto_match_payment(payment.name)
    except Exception:
        frappe.log_error(title="Portal Payment Auto-Match Error", message=frappe.get_traceback())

    return {"success": True, "payment": payment.name}
