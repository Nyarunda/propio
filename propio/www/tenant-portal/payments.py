from __future__ import unicode_literals

import frappe

from propio.portal_utils.auth import require_portal_user


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = 0

    tenant_name = require_portal_user("tenant")
    if not tenant_name:
        return

    context.title = "Tenant Payments"
    context.tenant = frappe.get_doc("Tenant", tenant_name)
    customer = frappe.db.get_value("Tenant", tenant_name, "customer") if frappe.db.has_column("Tenant", "customer") else None

    context.invoices = (
        frappe.get_all(
            "Sales Invoice",
            filters={"customer": customer, "outstanding_amount": [">", 0]},
            fields=["name", "posting_date", "outstanding_amount"],
            order_by="posting_date desc",
        )
        if customer
        else []
    )
    context.payments = frappe.get_all(
        "Payment Intake",
        filters={"tenant": tenant_name},
        fields=["name", "payment_reference", "payment_date", "amount", "payment_channel", "status"],
        order_by="payment_date desc",
        limit=20,
    )
