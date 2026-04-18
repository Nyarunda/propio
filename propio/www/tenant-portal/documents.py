from __future__ import unicode_literals

import frappe

from propio.portal_utils.auth import require_portal_user


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = 0

    tenant_name = require_portal_user("tenant")
    if not tenant_name:
        return

    context.title = "Tenant Documents"
    context.tenant = frappe.get_doc("Tenant", tenant_name)

    lease = frappe.db.get_value("Lease", {"tenant": tenant_name, "status": ["in", ["Active", "Expiring Soon"]]}, "name")

    files = []
    filters = []
    filters.append({"attached_to_doctype": "Tenant", "attached_to_name": tenant_name})
    if lease:
        filters.append({"attached_to_doctype": "Lease", "attached_to_name": lease})

    for f in filters:
        files.extend(
            frappe.get_all(
                "File",
                filters=f,
                fields=["name", "file_name", "file_url", "creation"],
                order_by="creation desc",
                limit=50,
            )
        )

    context.files = files
