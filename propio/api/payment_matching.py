from __future__ import unicode_literals

import re

import frappe
from frappe import _
from frappe.utils import getdate, nowdate


def _doctype_exists(doctype_name: str) -> bool:
    return bool(frappe.db.exists("DocType", doctype_name))


def auto_match_payment(doc_or_name, method=None):
    """Doc event + callable API wrapper."""
    if isinstance(doc_or_name, str):
        payment = frappe.get_doc("Payment Intake", doc_or_name)
    else:
        payment = doc_or_name

    return _auto_match_payment_doc(payment)


@frappe.whitelist()
def auto_match_payment_by_name(payment_intake_name):
    return auto_match_payment(payment_intake_name)


def _auto_match_payment_doc(payment):
    if payment.status not in ("Received", "Unmatched", "Partially Matched"):
        return {"status": "error", "message": "Payment not in matchable state"}

    candidates = find_matching_invoices(payment)
    if not candidates:
        payment.status = "Unmatched"
        payment.save(ignore_permissions=True)
        return {"status": "no_match", "message": "No matching invoices found"}

    remaining = float(payment.amount or 0)
    allocations = []

    for invoice in candidates:
        if remaining <= 0:
            break

        allocated = min(remaining, float(invoice.outstanding_amount or 0))
        if allocated <= 0:
            continue

        allocations.append(
            {
                "invoice": invoice.name,
                "allocated_amount": allocated,
                "allocation_date": nowdate(),
            }
        )
        remaining -= allocated

    if not allocations:
        return {"status": "no_match", "message": "Could not allocate payment"}

    apply_allocations(payment, allocations)
    payment.status = "Matched" if remaining == 0 else "Partially Matched"
    payment.save(ignore_permissions=True)

    if payment.status == "Matched":
        create_payment_entry(payment)

    return {"status": "success", "allocated": len(allocations), "remaining": remaining}


def find_matching_invoices(payment):
    customer = frappe.get_value("Tenant", payment.tenant, "customer")
    if not customer:
        return []

    open_invoices = frappe.get_all(
        "Sales Invoice",
        filters={"customer": customer, "docstatus": 1, "outstanding_amount": [">", 0]},
        fields=["name", "outstanding_amount", "posting_date", "due_date"],
        order_by="posting_date asc",
    )

    matched_invoices = []
    if payment.raw_reference:
        invoice_match = extract_invoice_from_reference(payment.raw_reference)
        if invoice_match:
            for inv in open_invoices:
                if inv.name == invoice_match:
                    matched_invoices.append(inv)
                    open_invoices.remove(inv)
                    break

    matched_invoices.extend(open_invoices)
    return matched_invoices


def extract_invoice_from_reference(reference):
    patterns = [
        r"(?:INV|SINV|ACC-SINV)[-\\s]*(\\d{4}[-\\s]*\\d+)",
        r"(?:Invoice|INV)[:\\s]*([A-Z0-9\\-]+)",
        r"([A-Z]{2,4}-\\d{4}-\\d{5,})",
    ]

    for pattern in patterns:
        match = re.search(pattern, reference or "", re.IGNORECASE)
        if not match:
            continue

        invoice_ref = match.group(1) if len(match.groups()) > 0 else match.group(0)
        invoice = frappe.db.exists("Sales Invoice", invoice_ref)
        if invoice:
            return invoice

    return None


def apply_allocations(payment, allocations):
    payment.set("allocations", [])

    for alloc in allocations:
        payment.append(
            "allocations",
            {
                "invoice": alloc["invoice"],
                "allocated_amount": alloc["allocated_amount"],
                "allocation_date": alloc["allocation_date"],
                "status": "Applied",
            },
        )


def create_payment_entry(payment):
    if not _doctype_exists("Payment Entry"):
        return None

    tenant = frappe.get_doc("Tenant", payment.tenant)
    customer = tenant.customer
    if not customer:
        return None

    payment_entry = frappe.get_doc(
        {
            "doctype": "Payment Entry",
            "payment_type": "Receive",
            "party_type": "Customer",
            "party": customer,
            "company": payment.company,
            "posting_date": nowdate(),
            "mode_of_payment": get_mode_of_payment(payment.payment_channel),
            "paid_amount": payment.amount,
            "received_amount": payment.amount,
            "source_exchange_rate": 1,
            "target_exchange_rate": 1,
            "reference_no": payment.payment_reference,
            "reference_date": getdate(payment.payment_date),
        }
    )

    paid_to_account = _get_company_receipt_account(payment.company)
    if paid_to_account:
        payment_entry.paid_to = paid_to_account
        payment_entry.paid_to_account_currency = frappe.db.get_value("Account", paid_to_account, "account_currency")

    for alloc in payment.get("allocations"):
        if alloc.status != "Applied":
            continue
        payment_entry.append(
            "references",
            {
                "reference_doctype": "Sales Invoice",
                "reference_name": alloc.invoice,
                "total_amount": get_invoice_total(alloc.invoice),
                "outstanding_amount": get_invoice_outstanding(alloc.invoice),
                "allocated_amount": alloc.allocated_amount,
            },
        )

    payment_entry.insert(ignore_permissions=True)
    payment_entry.submit()

    payment.payment_entry = payment_entry.name
    payment.status = "Posted"
    payment.save(ignore_permissions=True)

    return payment_entry.name


def _get_company_receipt_account(company):
    account = frappe.db.get_value("Company", company, "default_bank_account")
    if account and frappe.db.exists("Account", account):
        return account

    rows = frappe.get_all(
        "Account",
        filters={"company": company, "is_group": 0, "disabled": 0, "account_type": ["in", ["Bank", "Cash"]]},
        fields=["name"],
        order_by="modified desc",
        limit=1,
    )
    return rows[0].name if rows else None


def get_mode_of_payment(channel):
    mapping = {
        "M-Pesa": "Mobile Money",
        "Bank Transfer": "Bank Transfer",
        "Cheque": "Cheque",
        "Cash": "Cash",
        "Card": "Card",
        "EFT": "Electronic Fund Transfer",
        "RTGS": "RTGS",
        "SWIFT": "SWIFT",
    }
    return mapping.get(channel, "Bank Transfer")


def get_invoice_total(invoice_name):
    return frappe.db.get_value("Sales Invoice", invoice_name, "grand_total") or 0


def get_invoice_outstanding(invoice_name):
    return frappe.db.get_value("Sales Invoice", invoice_name, "outstanding_amount") or 0


@frappe.whitelist()
def get_arrears_summary():
    if not _doctype_exists("Sales Invoice"):
        return {"total_arrears": 0, "aging_breakdown": {}, "collection_rate": 0}

    total_arrears = (
        frappe.db.sql(
            """
            SELECT COALESCE(SUM(outstanding_amount), 0)
            FROM `tabSales Invoice`
            WHERE docstatus = 1
              AND outstanding_amount > 0
            """
        )[0][0]
        or 0
    )

    aging = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    invoices = frappe.db.sql(
        """
        SELECT outstanding_amount, due_date
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND outstanding_amount > 0
        """,
        as_dict=True,
    )

    today = getdate(nowdate())
    for inv in invoices:
        if not inv.due_date:
            continue
        days_overdue = (today - getdate(inv.due_date)).days
        if days_overdue <= 0:
            continue
        if days_overdue <= 30:
            aging["0-30"] += inv.outstanding_amount
        elif days_overdue <= 60:
            aging["31-60"] += inv.outstanding_amount
        elif days_overdue <= 90:
            aging["61-90"] += inv.outstanding_amount
        else:
            aging["90+"] += inv.outstanding_amount

    return {
        "total_arrears": total_arrears,
        "aging_breakdown": aging,
        "collection_rate": calculate_collection_rate(),
    }


@frappe.whitelist()
def calculate_collection_rate():
    current_month_start = frappe.utils.get_first_day(nowdate())

    billed = (
        frappe.db.sql(
            """
            SELECT COALESCE(SUM(grand_total), 0)
            FROM `tabSales Invoice`
            WHERE posting_date >= %s
              AND docstatus = 1
            """,
            current_month_start,
        )[0][0]
        or 0
    )

    collected = (
        frappe.db.sql(
            """
            SELECT COALESCE(SUM(paid_amount), 0)
            FROM `tabPayment Entry`
            WHERE posting_date >= %s
              AND docstatus = 1
              AND payment_type = 'Receive'
            """,
            current_month_start,
        )[0][0]
        or 0
    )

    if billed == 0:
        return 100

    return round((collected / billed) * 100, 2)
