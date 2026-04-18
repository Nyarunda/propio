from __future__ import unicode_literals

import frappe
from frappe.utils import getdate, nowdate


def _doctype_exists(doctype_name: str) -> bool:
    return bool(frappe.db.exists("DocType", doctype_name))


@frappe.whitelist()
def generate_owner_statement(owner_name, property_name, period_from, period_to):
    existing = frappe.db.exists(
        "Owner Statement",
        {
            "owner": owner_name,
            "property": property_name,
            "period_from": period_from,
            "period_to": period_to,
        },
    )
    if existing:
        return {"status": "exists", "statement": existing}

    collections = get_collections(owner_name, property_name, period_from, period_to)
    expenses = get_expenses(owner_name, property_name, period_from, period_to)
    management_fees = get_management_fees(owner_name, property_name, period_from, period_to)
    reserve_movement = calculate_reserve_movement(owner_name, property_name, period_from, period_to)

    total_collected = sum(c["amount"] for c in collections)
    total_expenses = sum(e["amount"] for e in expenses)
    total_fees = sum(f["amount"] for f in management_fees)

    net_income = total_collected - total_expenses - total_fees
    payout_due = net_income - reserve_movement

    statement = frappe.get_doc(
        {
            "doctype": "Owner Statement",
            "owner": owner_name,
            "property": property_name,
            "company": frappe.db.get_value("Property", property_name, "company"),
            "period_from": period_from,
            "period_to": period_to,
            "currency": get_property_currency(property_name),
            "rent_collected": total_collected,
            "operating_expenses": total_expenses,
            "management_fee": total_fees,
            "total_income": total_collected,
            "total_expenses": total_expenses + total_fees,
            "net_operating_income": net_income,
            "reserve_movement": reserve_movement,
            "payout_due": payout_due,
            "status": "Draft",
        }
    )

    for collection in collections:
        statement.append(
            "statement_lines",
            {
                "posting_date": collection["date"],
                "transaction_type": "Rent Collection",
                "description": collection["description"],
                "reference_doc": collection["reference"],
                "reference_doctype": "Payment Entry",
                "credit": collection["amount"],
                "debit": 0,
            },
        )

    for expense in expenses:
        statement.append(
            "statement_lines",
            {
                "posting_date": expense["date"],
                "transaction_type": "Operating Expense",
                "description": expense["description"],
                "reference_doc": expense["reference"],
                "reference_doctype": expense.get("reference_doctype"),
                "debit": expense["amount"],
                "credit": 0,
            },
        )

    for fee in management_fees:
        statement.append(
            "statement_lines",
            {
                "posting_date": fee["date"],
                "transaction_type": "Management Fee",
                "description": fee["description"],
                "reference_doc": fee["reference"],
                "reference_doctype": "Management Fee Run",
                "debit": fee["amount"],
                "credit": 0,
            },
        )

    if reserve_movement:
        statement.append(
            "statement_lines",
            {
                "posting_date": period_to,
                "transaction_type": "Reserve Transfer",
                "description": "Reserve fund movement",
                "debit": reserve_movement if reserve_movement > 0 else 0,
                "credit": abs(reserve_movement) if reserve_movement < 0 else 0,
            },
        )

    statement.insert(ignore_permissions=True)
    return {"status": "success", "statement": statement.name}


def get_collections(owner_name, property_name, period_from, period_to):
    if not _doctype_exists("Payment Entry Reference"):
        return []

    rows = frappe.db.sql(
        """
        SELECT
            pe.posting_date AS date,
            per.allocated_amount AS amount,
            CONCAT('Payment ', pe.name, ' for invoice ', per.reference_name) AS description,
            pe.name AS reference
        FROM `tabPayment Entry Reference` per
        INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
        INNER JOIN `tabSales Invoice` si ON si.name = per.reference_name
        WHERE per.reference_doctype = 'Sales Invoice'
          AND si.property = %(property)s
          AND pe.posting_date BETWEEN %(period_from)s AND %(period_to)s
          AND pe.docstatus = 1
          AND pe.payment_type = 'Receive'
        ORDER BY pe.posting_date ASC
        """,
        {"property": property_name, "period_from": period_from, "period_to": period_to},
        as_dict=True,
    )
    return rows


def get_expenses(owner_name, property_name, period_from, period_to):
    expenses = []

    if _doctype_exists("Work Order"):
        maintenance = frappe.db.sql(
            """
            SELECT
                posting_date AS date,
                COALESCE(total_cost, grand_total, 0) AS amount,
                CONCAT('Maintenance: ', COALESCE(title, name)) AS description,
                name AS reference
            FROM `tabWork Order`
            WHERE property = %(property)s
              AND posting_date BETWEEN %(from)s AND %(to)s
              AND docstatus = 1
            """,
            {"property": property_name, "from": period_from, "to": period_to},
            as_dict=True,
        )
        for row in maintenance:
            row["reference_doctype"] = "Work Order"
        expenses.extend(maintenance)

    if _doctype_exists("Purchase Invoice") and frappe.db.has_column("Purchase Invoice", "property"):
        vendor_bills = frappe.db.sql(
            """
            SELECT
                posting_date AS date,
                grand_total AS amount,
                CONCAT('Vendor Bill: ', supplier_name) AS description,
                name AS reference
            FROM `tabPurchase Invoice`
            WHERE property = %(property)s
              AND posting_date BETWEEN %(from)s AND %(to)s
              AND docstatus = 1
            """,
            {"property": property_name, "from": period_from, "to": period_to},
            as_dict=True,
        )
        for row in vendor_bills:
            row["reference_doctype"] = "Purchase Invoice"
        expenses.extend(vendor_bills)

    return expenses


def get_management_fees(owner_name, property_name, period_from, period_to):
    if not _doctype_exists("Management Fee Run"):
        return []

    rows = frappe.db.sql(
        """
        SELECT
            mfr.period_to AS date,
            mfr.fee_amount AS amount,
            CONCAT('Management Fee - ', ma.agreement_no) AS description,
            mfr.name AS reference
        FROM `tabManagement Fee Run` mfr
        INNER JOIN `tabManagement Agreement` ma ON ma.name = mfr.management_agreement
        WHERE ma.owner = %(owner)s
          AND ma.property = %(property)s
          AND mfr.period_to BETWEEN %(from)s AND %(to)s
          AND mfr.status = 'Calculated'
        """,
        {"owner": owner_name, "property": property_name, "from": period_from, "to": period_to},
        as_dict=True,
    )
    return rows


def calculate_reserve_movement(owner_name, property_name, period_from, period_to):
    agreement = frappe.db.get_value(
        "Management Agreement",
        {"owner": owner_name, "property": property_name, "status": "Active"},
        ["name", "reserve_percentage"],
    )
    if not agreement or not agreement[1]:
        return 0

    collections = get_collections(owner_name, property_name, period_from, period_to)
    expenses = get_expenses(owner_name, property_name, period_from, period_to)

    net_before_reserve = sum(c["amount"] for c in collections) - sum(e["amount"] for e in expenses)
    return (net_before_reserve * agreement[1]) / 100


def get_property_currency(property_name):
    if frappe.db.has_column("Property", "default_currency"):
        return frappe.db.get_value("Property", property_name, "default_currency") or "USD"

    company = frappe.db.get_value("Property", property_name, "company")
    return frappe.get_cached_value("Company", company, "default_currency") if company else "USD"


@frappe.whitelist()
def approve_owner_statement(statement_name):
    statement = frappe.get_doc("Owner Statement", statement_name)
    if statement.status != "Draft":
        return {"status": "error", "message": "Statement already processed"}

    statement.status = "Approved"
    statement.approved_by = frappe.session.user
    statement.approved_on = nowdate()
    statement.save(ignore_permissions=True)
    return {"status": "success", "statement": statement_name}


@frappe.whitelist()
def process_owner_payout(statement_name):
    statement = frappe.get_doc("Owner Statement", statement_name)
    if statement.status != "Approved":
        return {"status": "error", "message": "Statement must be approved first"}

    if (statement.payout_due or 0) <= 0:
        return {"status": "error", "message": "No payout due"}

    settlement_name = None
    if _doctype_exists("Owner Settlement"):
        settlement = frappe.get_doc(
            {
                "doctype": "Owner Settlement",
                "owner": statement.owner,
                "owner_statement": statement.name,
                "company": statement.company,
                "payment_mode": "Bank Transfer",
                "payout_amount": statement.payout_due,
                "payment_date": nowdate(),
                "status": "Draft",
            }
        )
        settlement.insert(ignore_permissions=True)
        settlement_name = settlement.name

    statement.status = "Paid"
    statement.save(ignore_permissions=True)

    return {"status": "success", "settlement": settlement_name}


@frappe.whitelist()
def download_owner_statement_pdf(statement_name):
    statement = frappe.get_doc("Owner Statement", statement_name)

    html = frappe.render_template(
        "propio/templates/owner_statement.html",
        {"doc": statement, "company": frappe.get_doc("Company", statement.company)},
    )
    pdf = frappe.utils.pdf.get_pdf(html)

    filename = f"Owner_Statement_{statement.name}.pdf"
    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": filename,
            "content": pdf,
            "attached_to_doctype": "Owner Statement",
            "attached_to_name": statement.name,
        }
    )
    file_doc.insert(ignore_permissions=True)

    return file_doc.file_url
