from __future__ import unicode_literals

import frappe

from propio.portal_utils.auth import require_portal_user


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = 0

    owner_name = require_portal_user("owner")
    if not owner_name:
        return

    context.title = "Owner Documents"
    context.owner = frappe.get_doc("Owner", owner_name)

    files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Owner", "attached_to_name": owner_name},
        fields=["name", "file_name", "file_url", "creation"],
        order_by="creation desc",
        limit=100,
    )

    if frappe.db.exists("DocType", "Owner Statement"):
        statement_names = frappe.get_all("Owner Statement", filters={"owner": owner_name}, pluck="name")
        if statement_names:
            files.extend(
                frappe.get_all(
                    "File",
                    filters={"attached_to_doctype": "Owner Statement", "attached_to_name": ["in", statement_names]},
                    fields=["name", "file_name", "file_url", "creation"],
                    order_by="creation desc",
                    limit=100,
                )
            )

    context.files = files
