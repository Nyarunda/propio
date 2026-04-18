from __future__ import unicode_literals

import frappe
from frappe import _

from propio.portal_utils.auth import get_tenant_for_user


def _first_existing_doctype(*doctype_names):
    for dt in doctype_names:
        if frappe.db.exists("DocType", dt):
            return dt
    return None


def _tenant_for_session():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Login required"), frappe.PermissionError)
    return get_tenant_for_user(user)


@frappe.whitelist()
def get_active_lease():
    tenant = _tenant_for_session()
    if not tenant:
        return {"requires_setup": True, "message": _("No tenant record is linked to this account yet.")}

    lease = frappe.db.get_value(
        "Lease",
        {"tenant": tenant, "status": ["in", ["Active", "Expiring Soon"]]},
        [
            "name",
            "tenant",
            "start_date",
            "end_date",
            "billing_cycle",
            "deposit_amount",
            "property",
        ],
        as_dict=True,
        order_by="start_date desc",
    )

    if not lease:
        return None

    lease["tenant_name"] = frappe.db.get_value("Tenant", tenant, "tenant_name") or tenant
    lease["lease_name"] = lease.name

    unit_name = None
    if frappe.db.exists("DocType", "Lease Unit"):
        unit_name = frappe.db.get_value("Lease Unit", {"parent": lease.name}, "unit")
    lease["unit_name"] = unit_name

    property_name = None
    if lease.get("property"):
        property_name = frappe.db.get_value("Property", lease.property, "property_name") or lease.property
    lease["property_name"] = property_name

    monthly_rent = 0
    if frappe.db.exists("DocType", "Lease Charge"):
        monthly_rent = (
            frappe.db.sql(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM `tabLease Charge`
                WHERE parent = %s
                  AND IFNULL(billable, 1) = 1
                  AND IFNULL(frequency, 'Monthly') = 'Monthly'
                """,
                lease.name,
            )[0][0]
            or 0
        )
    lease["monthly_rent"] = monthly_rent

    customer = frappe.db.get_value("Tenant", tenant, "customer") if frappe.db.has_column("Tenant", "customer") else None
    outstanding = 0
    if customer:
        outstanding = (
            frappe.db.sql(
                """
                SELECT COALESCE(SUM(outstanding_amount), 0)
                FROM `tabSales Invoice`
                WHERE customer = %s
                  AND docstatus = 1
                  AND outstanding_amount > 0
                """,
                customer,
            )[0][0]
            or 0
        )
    lease["outstanding_balance"] = outstanding

    next_due = None
    if customer:
        next_due = frappe.db.get_value(
            "Sales Invoice",
            {"customer": customer, "docstatus": 1, "outstanding_amount": [">", 0]},
            "due_date",
            order_by="due_date asc",
        )
    lease["next_due_date"] = next_due

    payment_method = ""
    if frappe.db.exists("DocType", "Payment Intake") and frappe.db.has_column("Payment Intake", "payment_channel"):
        payment_method = frappe.db.get_value(
            "Payment Intake",
            {"tenant": tenant},
            "payment_channel",
            order_by="payment_date desc",
        ) or ""
    lease["payment_method"] = payment_method

    return lease


@frappe.whitelist()
def get_recent_invoices(limit=10):
    tenant = _tenant_for_session()
    if not tenant:
        return []
    customer = frappe.db.get_value("Tenant", tenant, "customer") if frappe.db.has_column("Tenant", "customer") else None
    if not customer:
        return []

    return frappe.get_all(
        "Sales Invoice",
        filters={"customer": customer, "docstatus": 1},
        fields=["name", "grand_total", "outstanding_amount", "due_date", "posting_date", "status"],
        order_by="posting_date desc",
        limit_page_length=int(limit or 10),
    )


@frappe.whitelist()
def get_recent_maintenance(limit=10):
    tenant = _tenant_for_session()
    if not tenant:
        return []
    service_dt = _first_existing_doctype("Service Request", "Maintenance Request")
    if not service_dt or not frappe.db.has_column(service_dt, "tenant"):
        return []

    fields = ["name", "status", "creation"]
    for candidate in ("subject", "request_type", "priority"):
        if frappe.get_meta(service_dt).has_field(candidate):
            fields.append(candidate)

    return frappe.get_all(
        service_dt,
        filters={"tenant": tenant},
        fields=fields,
        order_by="creation desc",
        limit_page_length=int(limit or 10),
    )


@frappe.whitelist()
def create_maintenance_request(subject, description, priority="Medium"):
    tenant = _tenant_for_session()
    if not tenant:
        frappe.throw(_("No tenant record is linked to this account yet. Please contact your property manager."))

    service_dt = _first_existing_doctype("Service Request", "Maintenance Request")
    if not service_dt:
        frappe.throw(_("No maintenance request doctype is available."))

    lease = frappe.db.get_value(
        "Lease",
        {"tenant": tenant, "status": ["in", ["Active", "Expiring Soon"]]},
        "name",
        order_by="start_date desc",
    )

    property_name = frappe.db.get_value("Lease", lease, "property") if lease else None
    unit_name = frappe.db.get_value("Lease Unit", {"parent": lease}, "unit") if lease and frappe.db.exists("DocType", "Lease Unit") else None

    doc = frappe.new_doc(service_dt)
    if frappe.get_meta(service_dt).has_field("subject"):
        doc.subject = subject
    if frappe.get_meta(service_dt).has_field("request_type"):
        doc.request_type = subject
    if frappe.get_meta(service_dt).has_field("description"):
        doc.description = description
    if frappe.get_meta(service_dt).has_field("priority"):
        doc.priority = priority
    if frappe.get_meta(service_dt).has_field("tenant"):
        doc.tenant = tenant
    if lease and frappe.get_meta(service_dt).has_field("lease"):
        doc.lease = lease
    if property_name and frappe.get_meta(service_dt).has_field("property"):
        doc.property = property_name
    if unit_name and frappe.get_meta(service_dt).has_field("unit"):
        doc.unit = unit_name
    if frappe.get_meta(service_dt).has_field("status"):
        doc.status = "Open"

    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "doctype": service_dt}
