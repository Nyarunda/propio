from __future__ import unicode_literals

import frappe

from propio.portal_utils.auth import require_portal_user


def _get_property_list(owner_name):
    if frappe.db.exists("DocType", "Property Ownership"):
        ownerships = frappe.get_all(
            "Property Ownership",
            filters={"owner": owner_name, "status": "Active"},
            fields=["property", "ownership_percentage"],
        )
        props = []
        for o in ownerships:
            p = frappe.get_value("Property", o.property, ["property_name", "property_code", "city", "status"], as_dict=True) or {}
            props.append(
                {
                    "name": o.property,
                    "property_name": p.get("property_name") or o.property,
                    "property_code": p.get("property_code"),
                    "city": p.get("city"),
                    "status": p.get("status"),
                    "ownership_percentage": o.get("ownership_percentage") or 0,
                }
            )
        return props

    if frappe.db.has_column("Property", "owner"):
        rows = frappe.get_all(
            "Property",
            filters={"owner": owner_name},
            fields=["name", "property_name", "property_code", "city", "status"],
        )
        for r in rows:
            r["ownership_percentage"] = 100
        return rows

    return []


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = 0

    owner_name = require_portal_user("owner")
    if not owner_name:
        frappe.flags.redirect_location = "/login"
        return

    context.title = "Owner Portal"
    context.owner = frappe.get_doc("Owner", owner_name)

    properties = _get_property_list(owner_name)
    property_names = [p["name"] for p in properties]

    total_units = frappe.db.count("Unit", {"property": ["in", property_names]}) if property_names else 0
    occupied_units = (
        frappe.db.count("Unit", {"property": ["in", property_names], "occupancy_status": "Occupied"})
        if property_names
        else 0
    )

    recent_payouts = (
        frappe.db.sql(
            """
            SELECT COALESCE(SUM(payout_amount), 0)
            FROM `tabOwner Settlement`
            WHERE owner = %s
              AND payment_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """,
            owner_name,
        )[0][0]
        if frappe.db.exists("DocType", "Owner Settlement")
        else 0
    )

    pending_payout = (
        frappe.db.sql(
            """
            SELECT COALESCE(SUM(payout_due), 0)
            FROM `tabOwner Statement`
            WHERE owner = %s AND status = 'Approved'
            """,
            owner_name,
        )[0][0]
        if frappe.db.exists("DocType", "Owner Statement")
        else 0
    )

    context.dashboard_data = {
        "total_properties": len(property_names),
        "total_units": total_units,
        "occupied_units": occupied_units,
        "occupancy_rate": round((occupied_units / total_units * 100), 1) if total_units else 0,
        "recent_payouts": recent_payouts,
        "pending_payout": pending_payout,
    }

    context.properties = properties[:5]
    context.recent_statements = (
        frappe.get_all(
            "Owner Statement",
            filters={"owner": owner_name},
            fields=["name", "period_from", "period_to", "net_operating_income", "payout_due", "status"],
            order_by="period_to desc",
            limit=5,
        )
        if frappe.db.exists("DocType", "Owner Statement")
        else []
    )
