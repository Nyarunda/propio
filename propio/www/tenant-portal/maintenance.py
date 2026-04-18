from __future__ import unicode_literals

import frappe

from propio.portal_utils.auth import require_portal_user


def _resolve_request_doctype():
    for dt in ("Service Request", "Maintenance Request"):
        if frappe.db.exists("DocType", dt):
            return dt
    return None


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = 0

    tenant_name = require_portal_user("tenant")
    if not tenant_name:
        return

    context.title = "Tenant Maintenance"
    context.tenant = frappe.get_doc("Tenant", tenant_name)
    request_dt = _resolve_request_doctype()
    fields = ["name", "description", "creation", "status", "priority"]
    if request_dt and frappe.get_meta(request_dt).has_field("request_type"):
        fields.insert(1, "request_type")
    context.requests = (
        frappe.get_all(
            request_dt,
            filters={"tenant": tenant_name},
            fields=fields,
            order_by="creation desc",
        )
        if request_dt and frappe.db.has_column(request_dt, "tenant")
        else []
    )
