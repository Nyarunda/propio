from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, nowdate


def _doctype_exists(doctype_name: str) -> bool:
    return bool(frappe.db.exists("DocType", doctype_name))


def sync_occupancy(doc, method=None):
    """Doc event hook for Lease updates."""
    if doc.status == "Active":
        activate_lease(doc)
    elif doc.status == "Terminated":
        terminate_lease(doc)


def validate_lease(doc, method=None):
    """Main validation hook for Lease."""
    validate_dates(doc)
    validate_units(doc)
    validate_charges(doc)
    validate_no_overlap(doc)
    validate_tenant_status(doc)
    validate_property_status(doc)


def validate_dates(doc):
    if doc.end_date and doc.start_date and getdate(doc.end_date) <= getdate(doc.start_date):
        frappe.throw(_("End Date must be later than Start Date."))

    if doc.commencement_date and doc.start_date and getdate(doc.commencement_date) < getdate(doc.start_date):
        frappe.throw(_("Commencement Date cannot be before Start Date."))

    if doc.handover_date and doc.start_date and getdate(doc.handover_date) < getdate(doc.start_date):
        frappe.throw(_("Handover Date cannot be before Start Date."))


def validate_units(doc):
    if not doc.get("lease_units"):
        frappe.throw(_("At least one unit is required for a lease."))

    for row in doc.get("lease_units"):
        unit = frappe.get_cached_doc("Unit", row.unit)

        if unit.property != doc.property:
            frappe.throw(_("Unit {0} does not belong to Property {1}.").format(row.unit, doc.property))

        if doc.building and unit.building and unit.building != doc.building:
            frappe.throw(_("Unit {0} does not belong to Building {1}.").format(row.unit, doc.building))

        if unit.status != "Active":
            frappe.throw(_("Unit {0} is not active.").format(row.unit))


def validate_charges(doc):
    billable_charges = [c for c in doc.get("lease_charges") if c.billable]
    if not billable_charges:
        frappe.throw(_("At least one billable charge is required."))


def validate_no_overlap(doc):
    if doc.status not in ("Active", "Expiring Soon"):
        return

    for row in doc.get("lease_units"):
        if has_overlapping_lease(
            unit_name=row.unit,
            lease_name=doc.name,
            start_date=doc.start_date,
            end_date=doc.end_date,
        ):
            frappe.throw(_("Unit {0} already has an active lease for this period.").format(row.unit))


def validate_tenant_status(doc):
    tenant = frappe.get_cached_doc("Tenant", doc.tenant)
    if tenant.status != "Active":
        frappe.throw(_("Tenant {0} is not active.").format(doc.tenant))


def validate_property_status(doc):
    property_doc = frappe.get_cached_doc("Property", doc.property)
    if property_doc.status != "Active":
        frappe.throw(_("Property {0} is not active.").format(doc.property))


def has_overlapping_lease(doc=None, unit_name=None, lease_name=None, start_date=None, end_date=None):
    """
    Workflow/helper compatibility:
    - can be called with a Lease doc
    - or explicit args for a single unit
    """
    if doc is not None:
        for row in doc.get("lease_units"):
            if has_overlapping_lease(
                unit_name=row.unit,
                lease_name=doc.name,
                start_date=doc.start_date,
                end_date=doc.end_date,
            ):
                return True
        return False

    if not unit_name or not start_date or not end_date:
        return False

    overlapping = frappe.db.sql(
        """
        SELECT l.name
        FROM `tabLease` l
        INNER JOIN `tabLease Unit` lu ON lu.parent = l.name
        WHERE lu.unit = %(unit)s
          AND l.name != %(lease)s
          AND l.status IN ('Active', 'Expiring Soon')
          AND l.docstatus < 2
          AND (
            (l.start_date <= %(end_date)s AND l.end_date >= %(start_date)s)
          )
        LIMIT 1
        """,
        {
            "unit": unit_name,
            "lease": lease_name or "",
            "start_date": start_date,
            "end_date": end_date,
        },
    )

    return bool(overlapping)


def activate_lease(doc, method=None):
    if doc.status != "Active":
        return

    update_unit_occupancy(doc)
    create_occupancy_record(doc)
    generate_billing_schedule(doc)
    send_lease_activated_notification(doc)


def update_unit_occupancy(doc):
    for row in doc.get("lease_units"):
        frappe.db.set_value(
            "Unit",
            row.unit,
            {
                "occupancy_status": "Occupied",
                "availability_status": "Not Available",
            },
            update_modified=False,
        )


def create_occupancy_record(doc):
    if not _doctype_exists("Occupancy Record"):
        return

    for row in doc.get("lease_units"):
        occupancy = frappe.get_doc(
            {
                "doctype": "Occupancy Record",
                "lease": doc.name,
                "tenant": doc.tenant,
                "property": doc.property,
                "unit": row.unit,
                "check_in_date": doc.commencement_date or doc.start_date,
                "status": "Active",
            }
        )
        occupancy.insert(ignore_permissions=True)


def generate_billing_schedule(doc):
    if not _doctype_exists("Billing Schedule"):
        return

    frappe.enqueue(
        "propio.api.billing.generate_billing_schedule",
        queue="long",
        lease_name=doc.name,
        lease=doc.as_dict(),
    )


def send_lease_activated_notification(doc):
    if not _doctype_exists("Propio Notification"):
        return

    notification = frappe.get_doc(
        {
            "doctype": "Propio Notification",
            "notification_type": "Lease Activated",
            "priority": "Info",
            "reference_doctype": "Lease",
            "reference_name": doc.name,
            "subject": f"Lease {doc.name} has been activated",
            "message": f"Lease for {doc.tenant} on {doc.property} is now active.",
            "target_role": "Property Manager",
        }
    )
    notification.insert(ignore_permissions=True)


def terminate_lease(doc, method=None):
    if doc.status != "Terminated":
        return

    for row in doc.get("lease_units"):
        if not has_future_lease(row.unit, doc.name):
            frappe.db.set_value(
                "Unit",
                row.unit,
                {
                    "occupancy_status": "Vacant",
                    "availability_status": "Available",
                },
                update_modified=False,
            )

    close_occupancy_record(doc)
    check_outstanding_balance(doc)


def has_future_lease(unit_name, current_lease_name):
    future = frappe.db.sql(
        """
        SELECT l.name
        FROM `tabLease` l
        INNER JOIN `tabLease Unit` lu ON lu.parent = l.name
        WHERE lu.unit = %(unit)s
          AND l.name != %(lease)s
          AND l.status IN ('Approved', 'Active', 'Expiring Soon')
          AND l.start_date > CURDATE()
        LIMIT 1
        """,
        {"unit": unit_name, "lease": current_lease_name},
    )
    return bool(future)


def close_occupancy_record(doc):
    if not _doctype_exists("Occupancy Record"):
        return

    frappe.db.sql(
        """
        UPDATE `tabOccupancy Record`
        SET check_out_date = %(today)s,
            status = 'Closed'
        WHERE lease = %(lease)s
          AND status = 'Active'
        """,
        {"today": nowdate(), "lease": doc.name},
    )


def check_outstanding_balance(doc):
    if not _doctype_exists("Sales Invoice"):
        return

    if not frappe.db.has_column("Sales Invoice", "lease"):
        return

    outstanding = frappe.db.sql(
        """
        SELECT COALESCE(SUM(outstanding_amount), 0)
        FROM `tabSales Invoice`
        WHERE lease = %(lease)s
          AND docstatus = 1
          AND outstanding_amount > 0
        """,
        {"lease": doc.name},
    )

    amount = outstanding[0][0] if outstanding else 0
    if amount and amount > 0:
        frappe.msgprint(
            _("Warning: Lease {0} has outstanding balance of {1}.").format(doc.name, amount),
            alert=True,
        )


def renew_lease(source_lease, new_start_date, new_end_date, new_terms=None):
    source = frappe.get_doc("Lease", source_lease)

    new_lease = frappe.copy_doc(source)
    new_lease.lease_type = "Renewal"
    new_lease.parent_lease = source.name
    new_lease.version_no = (source.version_no or 1) + 1
    new_lease.start_date = new_start_date
    new_lease.end_date = new_end_date
    new_lease.status = "Draft"
    new_lease.approval_status = "Draft"

    if new_terms:
        for charge in new_lease.get("lease_charges"):
            for term in new_terms:
                if charge.charge_type == term.get("charge_type"):
                    charge.amount = term.get("new_amount", charge.amount)
                    charge.start_date = new_start_date

    new_lease.insert()

    source.status = "Renewed"
    source.save()

    return new_lease.name


def has_open_invoices(doc):
    if not _doctype_exists("Sales Invoice"):
        return False

    if not frappe.db.has_column("Sales Invoice", "lease"):
        return False

    open_invoices = frappe.db.sql(
        """
        SELECT name
        FROM `tabSales Invoice`
        WHERE lease = %(lease)s
          AND docstatus = 1
          AND outstanding_amount > 0
        LIMIT 1
        """,
        {"lease": doc.name},
    )

    return bool(open_invoices)


def get_lease_summary(lease_name):
    lease = frappe.get_doc("Lease", lease_name)

    total_monthly_rent = sum(
        [
            c.amount
            for c in lease.get("lease_charges")
            if c.billable and c.frequency == "Monthly" and c.amount
        ]
    )

    total_annual_rent = sum(
        [
            c.amount * 12 if c.frequency == "Monthly" else c.amount
            for c in lease.get("lease_charges")
            if c.billable and c.amount
        ]
    )

    return {
        "lease_no": lease.lease_no,
        "tenant": lease.tenant,
        "property": lease.property,
        "start_date": lease.start_date,
        "end_date": lease.end_date,
        "days_remaining": date_diff(lease.end_date, nowdate()) if lease.end_date else None,
        "monthly_rent": total_monthly_rent,
        "annual_rent": total_annual_rent,
        "status": lease.status,
        "approval_status": lease.approval_status,
    }
