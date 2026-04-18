from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import now_datetime

from propio.portal_utils.auth import get_tenant_for_user


def _resolve_request_doctype():
    for dt in ("Service Request", "Maintenance Request"):
        if frappe.db.exists("DocType", dt):
            return dt
    return None


def _meta_has(doctype_name, fieldname):
    return frappe.get_meta(doctype_name).has_field(fieldname)


def _tenant_for_session():
    user = frappe.session.user
    if not user or user == "Guest":
        return None
    return get_tenant_for_user(user)


def _active_lease_for_tenant(tenant):
    return frappe.db.get_value(
        "Lease",
        {"tenant": tenant, "status": ["in", ["Active", "Expiring Soon"]]},
        ["name", "property"],
        as_dict=True,
        order_by="start_date desc",
    )


def _unit_from_lease(lease_name):
    if not lease_name or not frappe.db.exists("DocType", "Lease Unit"):
        return None
    return frappe.db.get_value("Lease Unit", {"parent": lease_name}, "unit")


@frappe.whitelist()
def submit_maintenance_request(
    subject=None,
    description=None,
    priority="Medium",
    category=None,
    preferred_date=None,
    preferred_time=None,
    request_type=None,
):
    # Backward-compatible support for old payload:
    # { request_type, priority, description, preferred_time }
    subject = subject or request_type or "Maintenance Request"
    tenant = _tenant_for_session()
    if not tenant:
        return {"success": False, "message": _("No tenant record found. Please contact your property manager.")}

    request_dt = _resolve_request_doctype()
    if not request_dt:
        return {"success": False, "message": _("Maintenance request DocType is not configured")}

    if not subject:
        return {"success": False, "message": _("Subject is required")}
    if not description:
        return {"success": False, "message": _("Description is required")}

    lease = _active_lease_for_tenant(tenant)
    lease_name = lease.name if lease else None
    property_name = lease.property if lease else None
    unit = _unit_from_lease(lease_name)

    doc = {"doctype": request_dt}
    if _meta_has(request_dt, "subject"):
        doc["subject"] = subject
    if _meta_has(request_dt, "request_type"):
        doc["request_type"] = subject
    if _meta_has(request_dt, "priority"):
        doc["priority"] = priority
    if _meta_has(request_dt, "description"):
        doc["description"] = description
    if category and _meta_has(request_dt, "category"):
        doc["category"] = category
    if preferred_date and _meta_has(request_dt, "preferred_date"):
        doc["preferred_date"] = preferred_date
    if _meta_has(request_dt, "tenant"):
        doc["tenant"] = tenant
    if lease_name and _meta_has(request_dt, "lease"):
        doc["lease"] = lease_name
    if _meta_has(request_dt, "property"):
        doc["property"] = property_name
    if unit and _meta_has(request_dt, "unit"):
        doc["unit"] = unit
    if _meta_has(request_dt, "status"):
        doc["status"] = "Open"
    if preferred_time and _meta_has(request_dt, "preferred_time"):
        doc["preferred_time"] = preferred_time

    request = frappe.get_doc(doc)
    request.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"success": True, "request_id": request.name, "request": request.name}


@frappe.whitelist()
def get_maintenance_requests(limit=20, status=None):
    tenant = _tenant_for_session()
    if not tenant:
        return []

    request_dt = _resolve_request_doctype()
    if not request_dt or not _meta_has(request_dt, "tenant"):
        return []

    fields = ["name", "creation"]
    for candidate in (
        "subject",
        "request_type",
        "description",
        "status",
        "priority",
        "preferred_date",
        "preferred_time",
        "category",
        "images",
    ):
        if _meta_has(request_dt, candidate):
            fields.append(candidate)

    filters = {"tenant": tenant}
    if status:
        filters["status"] = status

    rows = frappe.get_all(
        request_dt,
        filters=filters,
        fields=fields,
        order_by="creation desc",
        limit_page_length=int(limit or 20),
    )

    for row in rows:
        if "subject" not in row or not row.get("subject"):
            row["subject"] = row.get("request_type") or row.get("name")
    return rows


@frappe.whitelist()
def get_maintenance_request_details(request_name):
    tenant = _tenant_for_session()
    if not tenant:
        return None

    request_dt = _resolve_request_doctype()
    if not request_dt:
        return None

    try:
        doc = frappe.get_doc(request_dt, request_name)
    except frappe.DoesNotExistError:
        return None

    if _meta_has(request_dt, "tenant") and doc.get("tenant") != tenant:
        frappe.throw(_("Permission denied"), frappe.PermissionError)

    result = {
        "name": doc.name,
        "creation": doc.creation,
        "subject": doc.get("subject") or doc.get("request_type") or doc.name,
    }
    for fieldname in (
        "description",
        "status",
        "priority",
        "category",
        "preferred_date",
        "preferred_time",
        "images",
        "resolution_notes",
        "resolved_date",
        "assigned_to",
    ):
        if _meta_has(request_dt, fieldname):
            result[fieldname] = doc.get(fieldname)
    return result


@frappe.whitelist()
def cancel_maintenance_request(request_name):
    tenant = _tenant_for_session()
    if not tenant:
        return {"success": False, "message": _("No tenant record found")}

    request_dt = _resolve_request_doctype()
    if not request_dt:
        return {"success": False, "message": _("Maintenance request DocType is not configured")}

    try:
        doc = frappe.get_doc(request_dt, request_name)
    except frappe.DoesNotExistError:
        return {"success": False, "message": _("Request not found")}

    if _meta_has(request_dt, "tenant") and doc.get("tenant") != tenant:
        return {"success": False, "message": _("Permission denied")}

    current_status = doc.get("status") if _meta_has(request_dt, "status") else "Open"
    if current_status != "Open":
        return {"success": False, "message": _("Cannot cancel request with status: {0}").format(current_status)}

    if _meta_has(request_dt, "status"):
        doc.status = "Cancelled"
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "message": _("Maintenance request cancelled successfully")}


@frappe.whitelist()
def get_tenant_dashboard_data():
    tenant = _tenant_for_session()
    if not tenant:
        return {"success": False, "message": "Tenant not found"}

    customer = frappe.db.get_value("Tenant", tenant, "customer") if frappe.db.has_column("Tenant", "customer") else None
    lease = frappe.db.get_value(
        "Lease",
        {"tenant": tenant, "status": ["in", ["Active", "Expiring Soon"]]},
        "name",
    )

    outstanding = 0
    if customer:
        outstanding = (
            frappe.db.sql(
                """
                SELECT COALESCE(SUM(outstanding_amount), 0)
                FROM `tabSales Invoice`
                WHERE customer = %s AND docstatus = 1 AND outstanding_amount > 0
                """,
                customer,
            )[0][0]
            or 0
        )

    request_dt = _resolve_request_doctype()
    open_requests = (
        frappe.db.count(
            request_dt,
            {"tenant": tenant, "status": ["not in", ["Resolved", "Closed", "Cancelled"]]},
        )
        if request_dt and frappe.db.has_column(request_dt, "tenant")
        else 0
    )

    next_due = None
    if customer:
        rows = frappe.db.sql(
            """
            SELECT due_date, outstanding_amount
            FROM `tabSales Invoice`
            WHERE customer = %s AND docstatus = 1 AND outstanding_amount > 0
            ORDER BY due_date ASC
            LIMIT 1
            """,
            customer,
            as_dict=True,
        )
        next_due = rows[0] if rows else None

    return {
        "success": True,
        "tenant": tenant,
        "lease": lease,
        "outstanding": outstanding,
        "open_requests": open_requests,
        "next_due": next_due,
        "timestamp": now_datetime(),
    }
