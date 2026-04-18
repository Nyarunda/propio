from __future__ import unicode_literals

import frappe
from frappe.utils import add_days, nowdate


def _doctype_exists(doctype_name: str) -> bool:
    return bool(frappe.db.exists("DocType", doctype_name))


def send_expiry_alerts():
    """Scheduled daily: create lease expiry alerts at configured intervals."""
    if not (_doctype_exists("Lease") and _doctype_exists("Propio Notification")):
        return

    today = nowdate()
    alert_days = (60, 30, 14, 7)

    for days in alert_days:
        expiry_date = add_days(today, days)
        leases = frappe.get_all(
            "Lease",
            filters={"status": "Active", "end_date": expiry_date},
            fields=["name", "tenant", "property", "end_date"],
        )
        for lease in leases:
            create_expiry_notification(lease, days)


def create_expiry_notification(lease, days):
    existing = frappe.db.exists(
        "Propio Notification",
        {
            "reference_doctype": "Lease",
            "reference_name": lease.name,
            "notification_type": f"Lease Expiring {days} Days",
        },
    )
    if existing:
        return

    notification = frappe.get_doc(
        {
            "doctype": "Propio Notification",
            "notification_type": f"Lease Expiring {days} Days",
            "priority": "Warning" if days <= 14 else "Info",
            "reference_doctype": "Lease",
            "reference_name": lease.name,
            "subject": f"Lease {lease.name} expiring in {days} days",
            "message": (
                f"Lease for {lease.tenant} on {lease.property} expires on {lease.end_date}. "
                f"{days} days remaining."
            ),
            "target_role": "Property Manager",
        }
    )
    notification.insert(ignore_permissions=True)


def create_arrears_notification(tenant_name, amount_due, days_overdue):
    if not _doctype_exists("Propio Notification"):
        return

    priority = "Critical" if days_overdue > 30 else "High" if days_overdue > 14 else "Warning"
    notification = frappe.get_doc(
        {
            "doctype": "Propio Notification",
            "notification_type": "Arrears Alert",
            "priority": priority,
            "reference_doctype": "Tenant",
            "reference_name": tenant_name,
            "subject": f"Tenant {tenant_name} has arrears of {amount_due}",
            "message": f"Tenant is {days_overdue} days overdue. Amount due: {amount_due}",
            "target_role": "Collections Officer",
        }
    )
    notification.insert(ignore_permissions=True)


def send_whatsapp_notification(phone_number, message):
    return None


def send_sms_notification(phone_number, message):
    return None
