from __future__ import unicode_literals

import frappe
from frappe.utils import add_days, add_months, get_first_day, get_last_day, nowdate


def _doctype_exists(doctype_name: str) -> bool:
    return bool(frappe.db.exists("DocType", doctype_name))


def _si_has(column_name: str) -> bool:
    return frappe.db.has_column("Sales Invoice", column_name)


# ============ DAILY TASKS ============

def daily_arrears_case_creation():
    """Create arrears cases for overdue invoices that don't already have an open case."""
    if not _doctype_exists("Arrears Case"):
        return 0

    clauses = [
        "si.docstatus = 1",
        "si.outstanding_amount > 0",
        "si.due_date < CURDATE()",
    ]
    select_fields = [
        "si.name AS invoice",
        "si.outstanding_amount",
        "DATEDIFF(CURDATE(), si.due_date) AS days_overdue",
    ]

    if _si_has("tenant"):
        select_fields.append("si.tenant AS tenant")
    else:
        select_fields.append("NULL AS tenant")

    if _si_has("lease"):
        select_fields.append("si.lease AS lease")
    else:
        select_fields.append("NULL AS lease")

    if _si_has("property"):
        select_fields.append("si.property AS property")
    else:
        select_fields.append("NULL AS property")

    overdue = frappe.db.sql(
        f"""
        SELECT {", ".join(select_fields)}
        FROM `tabSales Invoice` si
        WHERE {' AND '.join(clauses)}
        """,
        as_dict=True,
    )

    created = 0
    for inv in overdue:
        lease = inv.get("lease")
        tenant = inv.get("tenant")
        property_name = inv.get("property")

        if lease and not tenant:
            tenant = frappe.db.get_value("Lease", lease, "tenant")
        if lease and not property_name:
            property_name = frappe.db.get_value("Lease", lease, "property")

        if not tenant:
            continue

        if frappe.db.exists(
            "Arrears Case",
            {
                "tenant": tenant,
                "lease": lease,
                "status": "Open",
            },
        ):
            continue

        company = get_property_company(property_name)
        if not company:
            company = frappe.defaults.get_defaults().get("company")
        if not company:
            continue

        case = frappe.get_doc(
            {
                "doctype": "Arrears Case",
                "tenant": tenant,
                "lease": lease,
                "property": property_name,
                "company": company,
                "total_arrears": inv.outstanding_amount,
                "days_overdue": inv.days_overdue,
                "stage": "New",
                "status": "Open",
            }
        )
        case.insert(ignore_permissions=True)
        create_arrears_notification(case)
        created += 1

    if created:
        frappe.db.commit()
    return created


def update_expiring_leases():
    """Set active leases expiring in next 30 days to Expiring Soon."""
    if not _doctype_exists("Lease"):
        return 0

    threshold = add_days(nowdate(), 30)
    leases = frappe.get_all(
        "Lease",
        filters={"status": "Active", "end_date": ["<=", threshold]},
        pluck="name",
    )

    for lease_name in leases:
        frappe.db.set_value("Lease", lease_name, "status", "Expiring Soon")
        send_expiry_notification(lease_name)

    if leases:
        frappe.db.commit()
    return len(leases)


def send_overdue_notifications():
    """Create reminders for invoices overdue by more than 7 days."""
    if not _doctype_exists("Propio Notification"):
        return 0

    invoices = frappe.db.sql(
        """
        SELECT
            si.name,
            si.outstanding_amount,
            DATEDIFF(CURDATE(), si.due_date) AS days_overdue
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1
          AND si.outstanding_amount > 0
          AND si.due_date < DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        """,
        as_dict=True,
    )

    created = 0
    for inv in invoices:
        exists = frappe.db.exists(
            "Propio Notification",
            {
                "reference_doctype": "Sales Invoice",
                "reference_name": inv.name,
                "notification_type": "Overdue Reminder",
            },
        )
        if exists:
            continue

        notification = frappe.get_doc(
            {
                "doctype": "Propio Notification",
                "notification_type": "Overdue Reminder",
                "priority": "Critical" if inv.days_overdue > 30 else "Warning",
                "reference_doctype": "Sales Invoice",
                "reference_name": inv.name,
                "subject": f"Overdue Payment: {inv.outstanding_amount}",
                "message": (
                    f"Invoice {inv.name} is {inv.days_overdue} days overdue. "
                    f"Amount due: {inv.outstanding_amount}"
                ),
                "target_role": "Collections Officer",
            }
        )
        notification.insert(ignore_permissions=True)
        created += 1

    if created:
        frappe.db.commit()
    return created


# ============ WEEKLY TASKS ============

def weekly_owner_statement_generation():
    """Generate owner statements for active management agreements for prior month."""
    if not _doctype_exists("Management Agreement") or not _doctype_exists("Owner Statement"):
        return 0

    period_to = get_last_day(add_months(nowdate(), -1))
    period_from = get_first_day(period_to)

    agreements = frappe.get_all(
        "Management Agreement",
        filters={"status": "Active"},
        fields=["name", "owner", "property"],
    )

    generated = 0
    for agreement in agreements:
        exists = frappe.db.exists(
            "Owner Statement",
            {
                "owner": agreement.owner,
                "property": agreement.property,
                "period_from": period_from,
                "period_to": period_to,
            },
        )
        if exists:
            continue

        try:
            from propio.api.owner_statement import generate_owner_statement

            result = generate_owner_statement(
                agreement.owner,
                agreement.property,
                period_from,
                period_to,
            )
            if result.get("status") == "success":
                generated += 1
                send_statement_notification(result.get("statement"), agreement.owner)
        except Exception:
            frappe.log_error(
                title="Weekly Owner Statement Generation Error",
                message=frappe.get_traceback(),
            )

    if generated:
        frappe.db.commit()
    return generated


# ============ MONTHLY TASKS ============

def monthly_fee_calculation():
    """Calculate management fees for active agreements for prior month."""
    if not _doctype_exists("Management Agreement") or not _doctype_exists("Management Fee Run"):
        return 0

    period_to = get_last_day(add_months(nowdate(), -1))
    period_from = get_first_day(period_to)

    agreements = frappe.get_all(
        "Management Agreement",
        filters={"status": "Active"},
        fields=["name"],
    )

    calculated = 0
    for agreement in agreements:
        already = frappe.db.exists(
            "Management Fee Run",
            {
                "management_agreement": agreement.name,
                "period_from": period_from,
                "period_to": period_to,
            },
        )
        if already:
            continue

        try:
            from propio.api.management_fee import apply_fee_to_owner_statement, calculate_management_fee

            result = calculate_management_fee(agreement.name, period_from, period_to)
            if result.get("status") == "success":
                calculated += 1
                if should_auto_apply_fee(agreement.name):
                    fee_run_name = result.get("fee_run")
                    if fee_run_name:
                        apply_fee_to_owner_statement(fee_run_name)
        except Exception:
            frappe.log_error(
                title="Monthly Management Fee Calculation Error",
                message=frappe.get_traceback(),
            )

    if calculated:
        frappe.db.commit()
    return calculated


# ============ CLEANUP TASKS ============

def cleanup_old_notifications():
    """Delete Propio notifications older than 90 days."""
    if not _doctype_exists("Propio Notification"):
        return 0

    cutoff_date = add_days(nowdate(), -90)
    old_notifications = frappe.get_all("Propio Notification", filters={"creation": ["<", cutoff_date]}, pluck="name")

    for name in old_notifications:
        frappe.delete_doc("Propio Notification", name, force=True, ignore_permissions=True)

    if old_notifications:
        frappe.db.commit()
    return len(old_notifications)


# ============ HELPERS ============

def get_property_company(property_name):
    if not property_name:
        return None
    return frappe.db.get_value("Property", property_name, "company")


def create_arrears_notification(arrears_case):
    if not _doctype_exists("Propio Notification"):
        return

    notification = frappe.get_doc(
        {
            "doctype": "Propio Notification",
            "notification_type": "New Arrears Case",
            "priority": "Warning",
            "reference_doctype": "Arrears Case",
            "reference_name": arrears_case.name,
            "subject": f"New Arrears Case: {arrears_case.tenant}",
            "message": f"Tenant {arrears_case.tenant} has arrears of {arrears_case.total_arrears}",
            "target_role": "Collections Officer",
        }
    )
    notification.insert(ignore_permissions=True)


def send_expiry_notification(lease_name):
    if not _doctype_exists("Propio Notification"):
        return

    lease = frappe.get_doc("Lease", lease_name)
    notification = frappe.get_doc(
        {
            "doctype": "Propio Notification",
            "notification_type": "Lease Expiring",
            "priority": "Warning",
            "reference_doctype": "Lease",
            "reference_name": lease.name,
            "subject": f"Lease {lease.name} expiring soon",
            "message": f"Lease for {lease.tenant} on {lease.property} expires on {lease.end_date}",
            "target_role": "Property Manager",
        }
    )
    notification.insert(ignore_permissions=True)


def send_statement_notification(statement_name, owner_name):
    if not _doctype_exists("Propio Notification") or not statement_name:
        return

    notification = frappe.get_doc(
        {
            "doctype": "Propio Notification",
            "notification_type": "Owner Statement Ready",
            "priority": "Info",
            "reference_doctype": "Owner Statement",
            "reference_name": statement_name,
            "subject": "Owner Statement Ready",
            "message": "Your owner statement has been generated. Log in to view.",
            "target_role": "Owner",
        }
    )
    notification.insert(ignore_permissions=True)


def should_auto_apply_fee(agreement_name):
    return True


# ============ MANUAL TRIGGERS ============

@frappe.whitelist()
def trigger_daily_tasks():
    return {
        "arrears_cases": daily_arrears_case_creation(),
        "expiring_leases": update_expiring_leases(),
        "notifications": send_overdue_notifications(),
    }


@frappe.whitelist()
def trigger_weekly_tasks():
    return {
        "owner_statements": weekly_owner_statement_generation(),
    }


@frappe.whitelist()
def trigger_monthly_tasks():
    return {
        "fee_calculations": monthly_fee_calculation(),
    }
