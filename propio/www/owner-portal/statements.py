from __future__ import unicode_literals

import frappe

from propio.portal_utils.auth import require_portal_user


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = 0

    owner_name = require_portal_user("owner")
    if not owner_name:
        return

    context.title = "Owner Statements"
    context.owner = frappe.get_doc("Owner", owner_name)
    context.statements = (
        frappe.get_all(
            "Owner Statement",
            filters={"owner": owner_name},
            fields=[
                "name",
                "property",
                "period_from",
                "period_to",
                "rent_collected",
                "total_expenses",
                "management_fee",
                "net_operating_income",
                "payout_due",
                "status",
            ],
            order_by="period_to desc",
        )
        if frappe.db.exists("DocType", "Owner Statement")
        else []
    )
