from __future__ import unicode_literals

import frappe
from frappe.utils import nowdate


def _doctype_exists(doctype_name: str) -> bool:
    return bool(frappe.db.exists("DocType", doctype_name))


@frappe.whitelist()
def calculate_management_fee(agreement_name, period_from, period_to):
    agreement = frappe.get_doc("Management Agreement", agreement_name)
    if agreement.status != "Active":
        return {"status": "error", "message": "Agreement is not active"}

    basis_amount = calculate_basis_amount(agreement, period_from, period_to)
    if not basis_amount:
        return {"status": "error", "message": "No basis amount found for period"}

    total_fee = 0
    fee_breakdown = []

    for rule in agreement.get("fee_rules"):
        fee = calculate_fee_by_rule(rule, basis_amount, agreement)
        if fee <= 0:
            continue
        total_fee += fee
        fee_breakdown.append(
            {
                "fee_type": rule.fee_type,
                "calculation_method": rule.calculation_method,
                "basis": rule.basis,
                "amount": fee,
            }
        )

    fee_run = create_fee_run(agreement, period_from, period_to, basis_amount, total_fee, fee_breakdown)
    return {
        "status": "success",
        "fee_run": fee_run,
        "basis_amount": basis_amount,
        "total_fee": total_fee,
        "breakdown": fee_breakdown,
    }


def calculate_basis_amount(agreement, period_from, period_to):
    rules = agreement.get("fee_rules")
    if not rules:
        return 0

    basis = rules[0].basis or "Rent Collected"
    if basis == "Rent Collected":
        return get_rent_collected(agreement.property, period_from, period_to)
    if basis == "Rent Billed":
        return get_rent_billed(agreement.property, period_from, period_to)
    if basis == "Total Collected":
        return get_total_collected(agreement.property, period_from, period_to)
    if basis == "Occupied Units":
        return get_occupied_units_count(agreement.property)
    if basis == "Total Units":
        return get_total_units_count(agreement.property)
    return 0


def get_rent_collected(property_name, period_from, period_to):
    if not _doctype_exists("Payment Entry Reference"):
        return 0

    result = frappe.db.sql(
        """
        SELECT COALESCE(SUM(per.allocated_amount), 0)
        FROM `tabPayment Entry Reference` per
        INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
        INNER JOIN `tabSales Invoice` si ON si.name = per.reference_name
        WHERE per.reference_doctype = 'Sales Invoice'
          AND si.property = %s
          AND pe.posting_date BETWEEN %s AND %s
          AND pe.docstatus = 1
          AND pe.payment_type = 'Receive'
        """,
        (property_name, period_from, period_to),
    )
    return result[0][0] or 0


def get_rent_billed(property_name, period_from, period_to):
    result = frappe.db.sql(
        """
        SELECT COALESCE(SUM(grand_total), 0)
        FROM `tabSales Invoice`
        WHERE property = %s
          AND posting_date BETWEEN %s AND %s
          AND docstatus = 1
        """,
        (property_name, period_from, period_to),
    )
    return result[0][0] or 0


def get_total_collected(property_name, period_from, period_to):
    return get_rent_collected(property_name, period_from, period_to)


def get_occupied_units_count(property_name):
    return frappe.db.count("Unit", {"property": property_name, "occupancy_status": "Occupied", "status": "Active"})


def get_total_units_count(property_name):
    return frappe.db.count("Unit", {"property": property_name, "status": "Active"})


def calculate_fee_by_rule(rule, basis_amount, agreement):
    if rule.calculation_method == "Percentage":
        return (basis_amount * (rule.percentage_rate or 0)) / 100
    if rule.calculation_method == "Fixed Amount":
        return rule.fixed_amount or 0
    if rule.calculation_method == "Per Unit":
        units = basis_amount if basis_amount else get_total_units_count(agreement.property)
        return (rule.per_unit_amount or 0) * units
    if rule.calculation_method == "Hybrid":
        fixed = rule.fixed_amount or 0
        percentage = (basis_amount * (rule.percentage_rate or 0)) / 100
        return fixed + percentage
    if rule.calculation_method == "Tiered":
        return (basis_amount * (rule.percentage_rate or 0)) / 100
    return 0


def create_fee_run(agreement, period_from, period_to, basis_amount, total_fee, breakdown):
    if not _doctype_exists("Management Fee Run"):
        return None

    fee_run = frappe.get_doc(
        {
            "doctype": "Management Fee Run",
            "management_agreement": agreement.name,
            "owner": agreement.owner,
            "property": agreement.property,
            "company": agreement.company,
            "period_from": period_from,
            "period_to": period_to,
            "basis_amount": basis_amount,
            "fee_amount": total_fee,
            "status": "Calculated",
            "posting_status": "Draft",
        }
    )

    if _doctype_exists("Management Fee Run Line"):
        for item in breakdown:
            fee_run.append(
                "fee_run_lines",
                {
                    "source_type": "Fee Calculation",
                    "eligible_amount": basis_amount,
                    "calculated_fee": item["amount"],
                },
            )

    fee_run.insert(ignore_permissions=True)
    return fee_run.name


@frappe.whitelist()
def apply_fee_to_owner_statement(fee_run_name):
    if not _doctype_exists("Management Fee Run"):
        return {"status": "error", "message": "Management Fee Run DocType not found"}

    fee_run = frappe.get_doc("Management Fee Run", fee_run_name)
    if fee_run.posting_status != "Draft":
        return {"status": "error", "message": "Fee already applied"}

    statement = frappe.db.exists(
        "Owner Statement",
        {
            "owner": fee_run.owner,
            "property": fee_run.property,
            "period_from": fee_run.period_from,
            "period_to": fee_run.period_to,
        },
    )

    if not statement:
        statement_doc = frappe.get_doc(
            {
                "doctype": "Owner Statement",
                "owner": fee_run.owner,
                "property": fee_run.property,
                "company": fee_run.company,
                "period_from": fee_run.period_from,
                "period_to": fee_run.period_to,
                "currency": frappe.get_cached_value("Company", fee_run.company, "default_currency"),
                "status": "Draft",
            }
        )
        statement_doc.insert(ignore_permissions=True)
        statement = statement_doc.name

    owner_statement = frappe.get_doc("Owner Statement", statement)
    owner_statement.management_fee = (owner_statement.management_fee or 0) + (fee_run.fee_amount or 0)
    owner_statement.append(
        "statement_lines",
        {
            "posting_date": nowdate(),
            "transaction_type": "Management Fee",
            "description": f"Management Fee for {fee_run.period_from} to {fee_run.period_to}",
            "reference_doc": fee_run.name,
            "reference_doctype": "Management Fee Run",
            "debit": fee_run.fee_amount,
            "credit": 0,
        },
    )
    owner_statement.save(ignore_permissions=True)

    fee_run.posting_status = "Applied to Statement"
    fee_run.save(ignore_permissions=True)

    return {"status": "success", "statement": statement}
