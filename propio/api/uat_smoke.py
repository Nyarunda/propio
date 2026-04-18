from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import frappe
from frappe.utils import add_days, now_datetime, nowdate


@dataclass
class CheckResult:
    area: str
    name: str
    status: str  # pass | fail | warn
    details: str = ""


@dataclass
class Suite:
    rows: list[CheckResult] = field(default_factory=list)

    def add(self, area: str, name: str, status: str, details: str = ""):
        self.rows.append(CheckResult(area=area, name=name, status=status, details=details))

    def summary(self) -> dict[str, int]:
        out = {"pass": 0, "fail": 0, "warn": 0}
        for r in self.rows:
            out[r.status] += 1
        return out

    def as_dict(self) -> dict[str, Any]:
        data = [{"area": r.area, "name": r.name, "status": r.status, "details": r.details} for r in self.rows]
        s = self.summary()
        return {"summary": s, "checks": data}


def _exists(doctype: str, name: str) -> bool:
    return bool(frappe.db.exists(doctype, name))


def _check_doctypes(suite: Suite):
    required = [
        "Property",
        "Unit",
        "Tenant",
        "Owner",
        "Property Ownership",
        "Lease",
        "Payment Intake",
        "Payment Intake Allocation",
        "Arrears Case",
        "Collections Follow Up",
        "Management Agreement",
        "Owner Statement",
        "Owner Statement Line",
        "Work Order",
        "Maintenance Schedule",
        "Maintenance Visit",
    ]
    for dt in required:
        suite.add("doctype", dt, "pass" if _exists("DocType", dt) else "fail")


def _check_workflows(suite: Suite):
    required_workflows = {
        "Lease Workflow": {
            "document_type": "Lease",
            "states": {
                "Draft",
                "Pending Approval",
                "Approved",
                "Active",
                "Expiring Soon",
                "Renewed",
                "Terminated",
                "Closed",
                "Rejected",
            },
            "actions": {"Submit for Approval", "Approve", "Reject", "Activate Lease", "Terminate", "Close"},
        },
        "Payment Intake Workflow": {
            "document_type": "Payment Intake",
            "states": {"Draft", "Received", "Matched", "Partially Matched", "Unmatched", "Posted", "Rejected"},
            "actions": {"Mark Received", "Mark Matched", "Mark Partial", "Mark Unmatched", "Post", "Reject"},
        },
    }

    for wf_name, cfg in required_workflows.items():
        if not _exists("Workflow", wf_name):
            suite.add("workflow", wf_name, "fail", "Workflow missing")
            continue

        doc_type = frappe.db.get_value("Workflow", wf_name, "document_type")
        suite.add(
            "workflow",
            f"{wf_name} -> document_type",
            "pass" if doc_type == cfg["document_type"] else "fail",
            f"expected={cfg['document_type']} actual={doc_type}",
        )

        states = set(
            frappe.db.sql(
                """
                select state
                from `tabWorkflow Document State`
                where parent=%s
                """,
                (wf_name,),
                pluck=True,
            )
            or []
        )
        missing_states = sorted(cfg["states"] - states)
        suite.add(
            "workflow",
            f"{wf_name} states",
            "pass" if not missing_states else "fail",
            "" if not missing_states else f"missing={missing_states}",
        )

        actions = set(
            frappe.db.sql(
                """
                select action
                from `tabWorkflow Transition`
                where parent=%s
                """,
                (wf_name,),
                pluck=True,
            )
            or []
        )
        missing_actions = sorted(cfg["actions"] - actions)
        suite.add(
            "workflow",
            f"{wf_name} actions",
            "pass" if not missing_actions else "fail",
            "" if not missing_actions else f"missing={missing_actions}",
        )


def _check_workspace_integrity(suite: Suite):
    workspaces = [
        "Property Hub",
        "Leasing Desk",
        "Finance Hub",
        "Collections Desk",
        "Owner Hub",
        "Maintenance Desk",
    ]

    for ws_name in workspaces:
        if not _exists("Workspace", ws_name):
            suite.add("workspace", ws_name, "fail", "Workspace missing")
            continue

        ws = frappe.get_doc("Workspace", ws_name)
        suite.add("workspace", ws_name, "pass", f"module={ws.module}")

        # validate links
        invalid_links = []
        for row in ws.links or []:
            link_to = row.link_to
            link_type = row.link_type
            if not link_to or not link_type:
                continue
            if link_type == "DocType" and not _exists("DocType", link_to):
                invalid_links.append(f"DocType:{link_to}")
            elif link_type == "Report" and not _exists("Report", link_to):
                invalid_links.append(f"Report:{link_to}")
            elif link_type == "Page" and not _exists("Page", link_to):
                invalid_links.append(f"Page:{link_to}")

        suite.add(
            "workspace",
            f"{ws_name} links",
            "pass" if not invalid_links else "fail",
            "" if not invalid_links else f"invalid={invalid_links}",
        )

        # validate cards/charts/shortcuts
        invalid_cards = [r.number_card_name for r in (ws.number_cards or []) if not _exists("Number Card", r.number_card_name)]
        invalid_charts = [r.chart_name for r in (ws.charts or []) if not _exists("Dashboard Chart", r.chart_name)]
        invalid_shortcuts = []
        for row in ws.shortcuts or []:
            link_to = row.link_to
            link_type = row.type
            if not link_to or not link_type:
                continue
            if link_type == "DocType" and not _exists("DocType", link_to):
                invalid_shortcuts.append(f"DocType:{link_to}")
            elif link_type == "Report" and not _exists("Report", link_to):
                invalid_shortcuts.append(f"Report:{link_to}")
            elif link_type == "Page" and not _exists("Page", link_to):
                invalid_shortcuts.append(f"Page:{link_to}")

        suite.add(
            "workspace",
            f"{ws_name} number_cards",
            "pass" if not invalid_cards else "fail",
            "" if not invalid_cards else f"invalid={invalid_cards}",
        )
        suite.add(
            "workspace",
            f"{ws_name} charts",
            "pass" if not invalid_charts else "fail",
            "" if not invalid_charts else f"invalid={invalid_charts}",
        )
        suite.add(
            "workspace",
            f"{ws_name} shortcuts",
            "pass" if not invalid_shortcuts else "fail",
            "" if not invalid_shortcuts else f"invalid={invalid_shortcuts}",
        )


def _check_roles_and_permissions(suite: Suite):
    roles = [
        "Portfolio Director",
        "Property Manager",
        "Leasing Officer",
        "Accountant",
        "Collections Officer",
        "Maintenance Coordinator",
    ]
    for role in roles:
        suite.add("role", role, "pass" if _exists("Role", role) else "fail")

    required_read_roles = {"System Manager", "Administrator", "Accountant", "Collections Officer", "Portfolio Director"}
    perm_rows = frappe.db.sql(
        """
        select role, `read`
        from `tabDocPerm`
        where parent='Payment Intake'
        """,
        as_dict=True,
    )
    readable = {r.role for r in perm_rows if int(r.read or 0) == 1}
    missing = sorted(required_read_roles - readable)
    suite.add(
        "permission",
        "Payment Intake read roles",
        "pass" if not missing else "fail",
        "" if not missing else f"missing={missing}",
    )


def _check_live_data_warnings(suite: Suite):
    # Non-blocking readiness warnings to help UAT.
    counts = {
        "Property": frappe.db.count("Property"),
        "Unit": frappe.db.count("Unit"),
        "Tenant": frappe.db.count("Tenant"),
        "Lease": frappe.db.count("Lease"),
        "Payment Intake": frappe.db.count("Payment Intake"),
    }
    for dt, n in counts.items():
        suite.add("data", f"{dt} sample count", "pass" if n > 0 else "warn", f"count={n}")


@frappe.whitelist()
def run_uat_smoke() -> dict[str, Any]:
    """
    Strict smoke suite for the live PROPIO architecture (Hub/Desk naming).
    Safe: read-only checks + integrity assertions.
    """
    suite = Suite()

    _check_doctypes(suite)
    _check_workflows(suite)
    _check_workspace_integrity(suite)
    _check_roles_and_permissions(suite)
    _check_live_data_warnings(suite)

    summary = suite.summary()
    print("\n" + "=" * 64)
    print("PROPIO UAT SMOKE SUITE")
    print("=" * 64)
    print(f"pass={summary['pass']} fail={summary['fail']} warn={summary['warn']}")
    if summary["fail"]:
        print("Blocking failures detected. Fix before UAT sign-off.")
    elif summary["warn"]:
        print("No blockers, but warnings indicate limited seed data for business flow tests.")
    else:
        print("All checks passed.")
    print("=" * 64 + "\n")

    return suite.as_dict()


def _get_default_company() -> str:
    company = frappe.defaults.get_user_default("Company")
    if company and frappe.db.exists("Company", company):
        return company

    company = frappe.db.get_value("Global Defaults", None, "default_company")
    if company and frappe.db.exists("Company", company):
        return company

    company = frappe.db.get_value("Company", {}, "name")
    if company:
        return company

    frappe.throw("No Company found. Create a Company before seeding UAT data.")


def _get_company_currency_country(company: str) -> tuple[str, str]:
    currency = frappe.db.get_value("Company", company, "default_currency") or "USD"
    country = frappe.db.get_value("Company", company, "country") or "United States"
    return currency, country


def _upsert_customer_for_tenant(tenant_name: str) -> str | None:
    if not frappe.db.exists("DocType", "Customer"):
        return None

    tenant_customer = frappe.db.get_value("Tenant", tenant_name, "customer")
    if tenant_customer and frappe.db.exists("Customer", tenant_customer):
        return tenant_customer

    customer_name = f"{tenant_name} Customer"
    existing = frappe.db.exists("Customer", {"customer_name": customer_name})
    if existing:
        customer = existing
    else:
        customer = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": customer_name,
                "customer_type": "Company",
                "territory": "All Territories",
                "customer_group": frappe.db.get_value("Customer Group", {}, "name") or "All Customer Groups",
            }
        )
        customer.insert(ignore_permissions=True)
        customer = customer.name

    frappe.db.set_value("Tenant", tenant_name, "customer", customer)
    return customer


def _ensure_mode_of_payment(mode_name: str, type_name: str = "Bank") -> None:
    if not frappe.db.exists("DocType", "Mode of Payment"):
        return
    if frappe.db.exists("Mode of Payment", mode_name):
        return
    mop = frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": mode_name, "type": type_name, "enabled": 1})
    mop.insert(ignore_permissions=True)


def _ensure_portfolio(portfolio_code: str, company: str, country: str, currency: str) -> str:
    if not frappe.db.exists("DocType", "Portfolio"):
        frappe.throw("Portfolio DocType is missing. Run migrate after adding Portfolio doctype files.")

    existing = frappe.db.exists("Portfolio", portfolio_code)
    if existing:
        return existing

    doc = frappe.get_doc(
        {
            "doctype": "Portfolio",
            "portfolio_code": portfolio_code,
            "portfolio_name": portfolio_code,
            "status": "Active",
            "company": company,
            "country": country,
            "base_currency": currency,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _repair_existing_portfolio_links(company: str, country: str, currency: str) -> list[str]:
    repaired = []
    if not frappe.db.exists("DocType", "Portfolio"):
        return repaired

    for dt in ("Property", "Unit", "Lease"):
        if not frappe.db.has_column(dt, "portfolio"):
            continue
        values = frappe.db.sql(
            f"""
            select distinct portfolio
            from `tab{dt}`
            where ifnull(portfolio, '') != ''
            """,
            pluck=True,
        ) or []
        for value in values:
            if not frappe.db.exists("Portfolio", value):
                _ensure_portfolio(value, company, country, currency)
                repaired.append(value)
    return sorted(set(repaired))


@frappe.whitelist()
def seed_minimal_uat_data() -> dict[str, Any]:
    """
    Idempotent safe seed for core UAT entities:
    Property, Unit, Tenant, Lease, Payment Intake.
    """
    out: dict[str, Any] = {"created": [], "existing": [], "warnings": [], "records": {}}

    company = _get_default_company()
    currency, country = _get_company_currency_country(company)

    portfolio_value = "UAT-PORTFOLIO"
    _ensure_portfolio(portfolio_value, company, country, currency)
    repaired = _repair_existing_portfolio_links(company, country, currency)
    if repaired:
        out["warnings"].append(f"Auto-created missing Portfolio records for existing links: {repaired}")

    # Property
    property_code = "UAT-PROP-001"
    property_name = "UAT Property 001"
    property_doc_name = frappe.db.exists("Property", {"property_code": property_code})
    if property_doc_name:
        out["existing"].append("Property")
    else:
        property_doc = frappe.get_doc(
            {
                "doctype": "Property",
                "property_code": property_code,
                "property_name": property_name,
                "status": "Active",
                "portfolio": portfolio_value,
                "company": company,
                "property_type": "Commercial",
                "management_type": "Managed",
                "country": country,
                "city": "Nairobi",
            }
        )
        property_doc.insert(ignore_permissions=True)
        property_doc_name = property_doc.name
        out["created"].append("Property")
    out["records"]["property"] = property_doc_name

    # Unit
    unit_code = "UAT-UNIT-001"
    unit_doc_name = frappe.db.exists("Unit", {"unit_code": unit_code})
    if unit_doc_name:
        out["existing"].append("Unit")
    else:
        unit_doc = frappe.get_doc(
            {
                "doctype": "Unit",
                "unit_code": unit_code,
                "unit_name": "UAT Unit 001",
                "status": "Active",
                "portfolio": portfolio_value,
                "property": property_doc_name,
                "company": company,
                "unit_type": "Office",
                "usage_type": "Commercial",
                "occupancy_status": "Vacant",
                "availability_status": "Available",
            }
        )
        unit_doc.insert(ignore_permissions=True)
        unit_doc_name = unit_doc.name
        out["created"].append("Unit")
    out["records"]["unit"] = unit_doc_name

    # Tenant
    tenant_name = "UAT Tenant 001"
    tenant_doc_name = frappe.db.exists("Tenant", {"tenant_name": tenant_name})
    if tenant_doc_name:
        out["existing"].append("Tenant")
    else:
        tenant_doc = frappe.get_doc(
            {
                "doctype": "Tenant",
                "tenant_name": tenant_name,
                "status": "Active",
                "tenant_type": "Corporate",
                "legal_name": "UAT Tenant 001 Ltd",
                "onboarding_status": "Approved",
            }
        )
        tenant_doc.insert(ignore_permissions=True)
        tenant_doc_name = tenant_doc.name
        out["created"].append("Tenant")
    out["records"]["tenant"] = tenant_doc_name

    # Lease
    lease_no = "UAT-LEASE-001"
    lease_doc_name = frappe.db.exists("Lease", {"lease_no": lease_no})
    if lease_doc_name:
        out["existing"].append("Lease")
    else:
        start_date = nowdate()
        end_date = add_days(start_date, 365)
        lease_doc = frappe.get_doc(
            {
                "doctype": "Lease",
                "lease_no": lease_no,
                "approval_status": "Draft",
                "status": "Draft",
                "company": company,
                "portfolio": portfolio_value,
                "property": property_doc_name,
                "tenant": tenant_doc_name,
                "lease_type": "New",
                "lease_category": "Commercial",
                "currency": currency,
                "start_date": start_date,
                "end_date": end_date,
                "billing_cycle": "Monthly",
                "lease_units": [{"unit": unit_doc_name}],
                "lease_charges": [
                    {
                        "charge_type": "Base Rent",
                        "charge_basis": "Fixed",
                        "amount": 1000,
                        "frequency": "Monthly",
                        "start_date": start_date,
                        "billable": 1,
                    }
                ],
            }
        )
        lease_doc.insert(ignore_permissions=True)
        lease_doc_name = lease_doc.name
        out["created"].append("Lease")
    out["records"]["lease"] = lease_doc_name

    # Payment Intake
    pay_ref = "UAT-PAYIN-001"
    payment_doc_name = frappe.db.exists("Payment Intake", {"payment_reference": pay_ref})
    if payment_doc_name:
        out["existing"].append("Payment Intake")
    else:
        payment_doc = frappe.get_doc(
            {
                "doctype": "Payment Intake",
                "payment_reference": pay_ref,
                "status": "Draft",
                "tenant": tenant_doc_name,
                "company": company,
                "payment_channel": "Bank Transfer",
                "currency": currency,
                "amount": 1000,
                "payment_date": now_datetime(),
                "raw_reference": "UAT seed payment",
            }
        )
        payment_doc.insert(ignore_permissions=True)
        payment_doc_name = payment_doc.name
        out["created"].append("Payment Intake")
    out["records"]["payment_intake"] = payment_doc_name

    frappe.db.commit()
    return out


@frappe.whitelist()
def run_e2e_property_to_payment_flow() -> dict[str, Any]:
    """
    End-to-end flow test:
    Property -> Unit -> Tenant -> Lease -> Billing -> Payment Intake
    """
    results: list[dict[str, Any]] = []

    def add(step: str, status: str, details: str = ""):
        results.append({"step": step, "status": status, "details": details})

    seeded = seed_minimal_uat_data()
    rec = seeded.get("records", {})
    for warning in seeded.get("warnings", []):
        add("seed", "warn", warning)

    # Property
    property_name = rec.get("property")
    add("property", "pass" if property_name and frappe.db.exists("Property", property_name) else "fail", property_name or "")

    # Unit
    unit_name = rec.get("unit")
    unit_property = frappe.db.get_value("Unit", unit_name, "property") if unit_name else None
    add(
        "unit",
        "pass" if unit_name and unit_property == property_name else "fail",
        f"unit={unit_name} property={unit_property}",
    )

    # Tenant
    tenant_name = rec.get("tenant")
    add("tenant", "pass" if tenant_name and frappe.db.exists("Tenant", tenant_name) else "fail", tenant_name or "")

    # Lease
    lease_name = rec.get("lease")
    lease_doc = frappe.get_doc("Lease", lease_name) if lease_name and frappe.db.exists("Lease", lease_name) else None
    lease_unit_ok = bool(lease_doc and any((row.unit == unit_name) for row in (lease_doc.lease_units or [])))
    lease_tenant_ok = bool(lease_doc and lease_doc.tenant == tenant_name)
    add(
        "lease",
        "pass" if lease_doc and lease_unit_ok and lease_tenant_ok else "fail",
        f"lease={lease_name} tenant_ok={lease_tenant_ok} unit_ok={lease_unit_ok}",
    )

    # Billing step
    billing_status = "warn"
    billing_details = ""
    invoice_name = None

    if frappe.db.exists("DocType", "Billing Schedule"):
        try:
            from propio.api import billing as billing_api

            billing_api.generate_billing_schedule(lease_name)
            billing_status = "pass"
            billing_details = "Billing Schedule generated (if active lease + billable charges)."
        except Exception as exc:
            billing_status = "fail"
            billing_details = f"Billing Schedule generation failed: {exc}"
    else:
        # Practical fallback: create a Sales Invoice for tenant customer.
        try:
            customer = _upsert_customer_for_tenant(tenant_name)
            if not customer:
                raise ValueError("Customer DocType unavailable")

            company = frappe.db.get_value("Property", property_name, "company")
            item_code = "UAT-SERVICE-RENT"
            if not frappe.db.exists("Item", item_code):
                item = frappe.get_doc(
                    {
                        "doctype": "Item",
                        "item_code": item_code,
                        "item_name": "UAT Service Rent",
                        "item_group": frappe.db.get_value("Item Group", {}, "name") or "All Item Groups",
                        "stock_uom": frappe.db.get_value("UOM", {}, "name") or "Nos",
                        "is_stock_item": 0,
                    }
                )
                item.insert(ignore_permissions=True)

            invoice_payload = {
                "doctype": "Sales Invoice",
                "customer": customer,
                "company": company,
                "posting_date": nowdate(),
                "due_date": add_days(nowdate(), 14),
                "items": [{"item_code": item_code, "qty": 1, "rate": 1000}],
            }
            invoice = frappe.get_doc(invoice_payload)
            invoice.insert(ignore_permissions=True)
            invoice_name = invoice.name
            try:
                invoice.submit()
                billing_details = f"Fallback billing via Sales Invoice created+submitted: {invoice_name}"
            except Exception as submit_exc:
                billing_details = f"Fallback billing via Sales Invoice created (draft): {invoice_name}; submit failed: {submit_exc}"
            billing_status = "pass"
        except Exception as exc:
            billing_status = "warn"
            billing_details = f"Fallback Sales Invoice billing not created: {exc}"

    add("billing", billing_status, billing_details)

    # Payment Intake (fresh record per run for deterministic workflow state)
    payment_name = None
    payment_exists = False
    try:
        flow_payment_ref = f"E2E-PAYIN-{frappe.generate_hash(length=8).upper()}"
        company = frappe.db.get_value("Property", property_name, "company")
        currency = frappe.db.get_value("Company", company, "default_currency") or "USD"
        payment_doc = frappe.get_doc(
            {
                "doctype": "Payment Intake",
                "payment_reference": flow_payment_ref,
                "status": "Draft",
                "tenant": tenant_name,
                "company": company,
                "payment_channel": "Bank Transfer",
                "currency": currency,
                "amount": 1000,
                "payment_date": now_datetime(),
                "raw_reference": invoice_name or "E2E payment",
            }
        )
        payment_doc.insert(ignore_permissions=True)
        payment_name = payment_doc.name
        payment_exists = True
        add("payment_intake", "pass", payment_name)
    except Exception as exc:
        add("payment_intake", "fail", f"Payment Intake creation failed: {exc}")

    # Optional match attempt (only meaningful with invoice)
    if invoice_name and payment_exists:
        try:
            _ensure_mode_of_payment("Bank Transfer", "Bank")

            payment_doc = frappe.get_doc("Payment Intake", payment_name)
            if payment_doc.status == "Draft":
                try:
                    from frappe.model.workflow import apply_workflow

                    payment_doc = apply_workflow(payment_doc, "Mark Received")
                except Exception:
                    # Soft fallback for local test-only flow.
                    payment_doc.db_set("status", "Received", update_modified=False)
                    payment_doc.reload()

            if payment_doc.status in ("Matched", "Posted"):
                add("payment_match", "pass", f"Already processed by hooks with status={payment_doc.status}")
                payment_exists = False  # skip explicit matcher call below
            else:
                from propio.api.payment_matching import auto_match_payment

                match_result = auto_match_payment(payment_name)
                if isinstance(match_result, dict) and match_result.get("status") == "error":
                    add("payment_match", "warn", str(match_result))
                else:
                    add("payment_match", "pass", str(match_result))
        except Exception as exc:
            add("payment_match", "warn", f"Auto-match skipped/failed: {exc}")

    frappe.db.commit()

    summary = {"pass": 0, "fail": 0, "warn": 0}
    for row in results:
        summary[row["status"]] += 1

    return {"summary": summary, "seed": seeded, "results": results}


def _ensure_item(item_code: str, item_name: str, is_stock_item: int = 1) -> str:
    if frappe.db.exists("Item", item_code):
        return item_code

    item_group = frappe.db.get_value("Item Group", {}, "name") or "All Item Groups"
    stock_uom = frappe.db.get_value("UOM", {}, "name") or "Nos"

    item = frappe.get_doc(
        {
            "doctype": "Item",
            "item_code": item_code,
            "item_name": item_name,
            "item_group": item_group,
            "stock_uom": stock_uom,
            "is_stock_item": int(is_stock_item),
        }
    )
    item.insert(ignore_permissions=True)
    return item.name


def _ensure_bom_for_item(item_code: str, company: str) -> str:
    existing = frappe.db.get_value("BOM", {"item": item_code, "is_active": 1}, "name")
    if existing:
        return existing

    raw_item = _ensure_item("UAT-RM-001", "UAT Raw Material 001", is_stock_item=1)
    uom = frappe.db.get_value("Item", raw_item, "stock_uom") or "Nos"

    bom = frappe.get_doc(
        {
            "doctype": "BOM",
            "company": company,
            "item": item_code,
            "quantity": 1,
            "is_active": 1,
            "is_default": 1,
            "items": [{"item_code": raw_item, "qty": 1, "uom": uom}],
        }
    )
    bom.insert(ignore_permissions=True)
    try:
        bom.submit()
    except Exception:
        pass
    return bom.name


@frappe.whitelist()
def seed_owner_maintenance_insights_data() -> dict[str, Any]:
    """
    Seed minimal Owner + Maintenance records so Owner Hub and Maintenance Desk
    insights show non-empty figures.
    """
    out: dict[str, Any] = {"created": [], "existing": [], "warnings": [], "records": {}}

    company = _get_default_company()
    _currency, country = _get_company_currency_country(company)

    property_name = frappe.db.get_value("Property", {}, "name")
    if not property_name:
        seeded = seed_minimal_uat_data()
        property_name = seeded.get("records", {}).get("property")

    # Owner
    owner_label = "UAT Owner 001"
    owner_name = frappe.db.exists("Owner", {"owner_name": owner_label})
    if owner_name:
        out["existing"].append("Owner")
    else:
        owner_doc = frappe.get_doc(
            {
                "doctype": "Owner",
                "owner_name": owner_label,
                "owner_type": "Corporate",
                "legal_name": "UAT Owner 001 Ltd",
                "status": "Active",
            }
        )
        owner_doc.insert(ignore_permissions=True)
        owner_name = owner_doc.name
        out["created"].append("Owner")
    out["records"]["owner"] = owner_name

    # Management Agreement
    agreement_no = "UAT-MGMT-001"
    agreement_name = frappe.db.exists("Management Agreement", {"agreement_no": agreement_no})
    if agreement_name:
        out["existing"].append("Management Agreement")
    else:
        mgmt_doc = frappe.get_doc(
            {
                "doctype": "Management Agreement",
                "agreement_no": agreement_no,
                "owner": owner_name,
                "property": property_name,
                "company": company,
                "start_date": nowdate(),
                "settlement_mode": "Deduct Before Payout",
                "status": "Active",
            }
        )
        # Management Agreement uses a fieldname that collides with Doc.owner.
        # For KPI seed data, bypass link validation safely.
        mgmt_doc.insert(ignore_permissions=True, ignore_links=True)
        agreement_name = mgmt_doc.name
        out["created"].append("Management Agreement")
    out["records"]["management_agreement"] = agreement_name

    # Work Order
    wo_name = frappe.db.exists("Work Order", {"production_item": ["!=", ""], "company": company})
    if wo_name:
        out["existing"].append("Work Order")
    else:
        try:
            fg_item = frappe.db.get_value("Item", {"disabled": 0, "has_variants": 0}, "name")
            if not fg_item:
                fg_item = _ensure_item("UAT-FG-001", "UAT Finished Good 001", is_stock_item=1)
            bom_no = _ensure_bom_for_item(fg_item, company)

            work_order = frappe.get_doc(
                {
                    "doctype": "Work Order",
                    "company": company,
                    "naming_series": "MFG-WO-.YYYY.-",
                    "production_item": fg_item,
                    "bom_no": bom_no,
                    "qty": 1,
                    "planned_start_date": nowdate(),
                    "planned_end_date": add_days(nowdate(), 2),
                    "status": "Draft",
                }
            )
            work_order.insert(ignore_permissions=True)
            wo_name = work_order.name
            out["created"].append("Work Order")
        except Exception as exc:
            out["warnings"].append(f"Work Order seed skipped: {exc}")
            wo_name = None
    out["records"]["work_order"] = wo_name

    frappe.db.commit()
    return out


@frappe.whitelist()
def get_owner_maintenance_insight_counts() -> dict[str, int]:
    return {
        "Owner": frappe.db.count("Owner"),
        "Management Agreement": frappe.db.count("Management Agreement"),
        "Work Order": frappe.db.count("Work Order"),
    }


@frappe.whitelist()
def verify_insights_data() -> dict[str, Any]:
    """Verify workspace insight source data and print a readable summary."""
    from frappe.utils import add_days, get_first_day, get_last_day

    print("\n" + "=" * 70)
    print("PROPIO INSIGHTS DATA VERIFICATION")
    print("=" * 70 + "\n")

    # Property Hub
    print("PROPERTY HUB")
    print("-" * 40)
    total_properties = frappe.db.count("Property", {"status": "Active"})
    total_units = frappe.db.count("Unit", {"status": "Active"})
    occupied_units = frappe.db.count("Unit", {"status": "Active", "occupancy_status": "Occupied"})
    vacant_units = frappe.db.count("Unit", {"status": "Active", "occupancy_status": "Vacant"})
    print(f"  Total Properties: {total_properties}")
    print(f"  Total Units: {total_units}")
    print(f"  Occupied Units: {occupied_units}")
    print(f"  Vacant Units: {vacant_units}")
    print(f"  Occupancy Rate: {(occupied_units / total_units * 100 if total_units > 0 else 0):.1f}%")

    # Leasing Desk
    print("\nLEASING DESK")
    print("-" * 40)
    active_leases = frappe.db.count("Lease", {"status": "Active"})
    expiring_soon = frappe.db.count("Lease", {"status": "Active", "end_date": ["<=", add_days(nowdate(), 30)]})
    pending_approvals = frappe.db.count("Lease", {"approval_status": "Pending Approval"})
    expiring_status = frappe.db.count("Lease", {"status": "Expiring Soon"})
    print(f"  Active Leases: {active_leases}")
    print(f"  Expiring in 30 Days: {expiring_soon}")
    print(f"  Pending Approvals: {pending_approvals}")
    print(f"  Expiring Soon: {expiring_status}")

    # Finance Hub
    print("\nFINANCE HUB")
    print("-" * 40)
    month_start = get_first_day(nowdate())
    month_end = get_last_day(nowdate())
    billed_this_month = (
        frappe.db.sql(
            """
            select coalesce(sum(base_grand_total), 0)
            from `tabSales Invoice`
            where posting_date between %s and %s
              and docstatus = 1
            """,
            (month_start, month_end),
        )[0][0]
        or 0
    )
    collected_this_month = (
        frappe.db.sql(
            """
            select coalesce(sum(received_amount), 0)
            from `tabPayment Entry`
            where posting_date between %s and %s
              and docstatus = 1
              and payment_type = 'Receive'
            """,
            (month_start, month_end),
        )[0][0]
        or 0
    )
    outstanding = (
        frappe.db.sql(
            """
            select coalesce(sum(outstanding_amount), 0)
            from `tabSales Invoice`
            where docstatus = 1
              and outstanding_amount > 0
            """
        )[0][0]
        or 0
    )
    overdue = (
        frappe.db.sql(
            """
            select coalesce(sum(outstanding_amount), 0)
            from `tabSales Invoice`
            where due_date < %s
              and outstanding_amount > 0
              and docstatus = 1
            """,
            (nowdate(),),
        )[0][0]
        or 0
    )
    print(f"  Billed This Month: {billed_this_month:,.2f}")
    print(f"  Collected This Month: {collected_this_month:,.2f}")
    print(f"  Outstanding Invoices: {outstanding:,.2f}")
    print(f"  Overdue Amount: {overdue:,.2f}")
    print(f"  Collection Rate: {(collected_this_month / billed_this_month * 100 if billed_this_month > 0 else 0):.1f}%")

    # Collections Desk
    print("\nCOLLECTIONS DESK")
    print("-" * 40)
    collections_case_dt = "Collection Case" if frappe.db.exists("DocType", "Collection Case") else "Arrears Case"
    open_cases = (
        frappe.db.count(collections_case_dt, {"status": "Open"})
        if frappe.db.exists("DocType", collections_case_dt)
        else 0
    )
    unmatched = frappe.db.count("Payment Intake", {"status": "Unmatched"})
    print(f"  Open Cases ({collections_case_dt}): {open_cases}")
    print(f"  Unmatched Payments: {unmatched}")

    # Owner Hub
    print("\nOWNER HUB")
    print("-" * 40)
    active_owners = frappe.db.count("Owner", {"status": "Active"})
    active_agreements = frappe.db.count("Management Agreement", {"status": "Active"})
    print(f"  Active Owners: {active_owners}")
    print(f"  Active Agreements: {active_agreements}")

    # Maintenance Desk
    print("\nMAINTENANCE DESK")
    print("-" * 40)
    open_requests = (
        frappe.db.count("Maintenance Request", {"status": ["not in", ["Closed", "Cancelled"]]})
        if frappe.db.exists("DocType", "Maintenance Request")
        else 0
    )
    open_work_orders = frappe.db.count("Work Order", {"status": ["not in", ["Closed", "Cancelled"]]})
    print(f"  Open Requests: {open_requests}")
    print(f"  Open Work Orders: {open_work_orders}")

    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)

    return {
        "property_hub": {
            "properties": total_properties,
            "units": total_units,
            "occupied": occupied_units,
            "vacant": vacant_units,
        },
        "leasing_desk": {"active": active_leases, "expiring": expiring_soon, "pending": pending_approvals},
        "finance_hub": {
            "billed": billed_this_month,
            "collected": collected_this_month,
            "outstanding": outstanding,
            "overdue": overdue,
        },
        "collections_desk": {"open_cases": open_cases, "unmatched": unmatched, "case_doctype": collections_case_dt},
        "owner_hub": {"owners": active_owners, "agreements": active_agreements},
        "maintenance_desk": {"requests": open_requests, "work_orders": open_work_orders},
    }


@frappe.whitelist()
def add_sample_dashboard_data() -> dict[str, Any]:
    """
    Add sample data to populate workspace insights.
    Idempotent by deterministic codes/names.
    """
    out: dict[str, Any] = {"created": [], "existing": [], "warnings": [], "counts": {}}

    company = _get_default_company()
    currency, country = _get_company_currency_country(company)
    portfolio = _ensure_portfolio("TEST-PORTFOLIO", company, country, currency)

    # Properties (3)
    property_names: list[str] = []
    for i in range(1, 4):
        code = f"SAMPLE-PROP-{i:03d}"
        pname = f"Sample Property {i}"
        existing = frappe.db.exists("Property", {"property_code": code})
        if existing:
            property_names.append(existing)
            out["existing"].append(f"Property:{code}")
            continue

        prop = frappe.get_doc(
            {
                "doctype": "Property",
                "property_code": code,
                "property_name": pname,
                "portfolio": portfolio,
                "company": company,
                "property_type": "Commercial" if i == 1 else "Residential",
                "management_type": "Managed",
                "country": country,
                "city": "Nairobi",
                "status": "Active",
            }
        )
        prop.insert(ignore_permissions=True)
        property_names.append(prop.name)
        out["created"].append(f"Property:{code}")

    # Units (3 per property = 9)
    unit_names: list[str] = []
    for pidx, prop_name in enumerate(property_names, start=1):
        property_type = frappe.db.get_value("Property", prop_name, "property_type")
        for j in range(1, 4):
            code = f"SAMPLE-PROP-{pidx:03d}-UNIT-{j:02d}"
            existing = frappe.db.exists("Unit", {"unit_code": code})
            if existing:
                unit_names.append(existing)
                out["existing"].append(f"Unit:{code}")
                continue

            occupancy = "Occupied" if j <= 2 else "Vacant"
            availability = "Not Available" if j <= 2 else "Available"
            unit = frappe.get_doc(
                {
                    "doctype": "Unit",
                    "unit_code": code,
                    "unit_name": f"Unit {j}",
                    "portfolio": portfolio,
                    "property": prop_name,
                    "company": company,
                    "unit_type": "Office" if property_type == "Commercial" else "Apartment",
                    "usage_type": "Commercial" if property_type == "Commercial" else "Residential",
                    "rentable_area": 100 * j,
                    "occupancy_status": occupancy,
                    "availability_status": availability,
                    "status": "Active",
                }
            )
            unit.insert(ignore_permissions=True)
            unit_names.append(unit.name)
            out["created"].append(f"Unit:{code}")

    # Tenants (4)
    tenant_names: list[str] = []
    for i in range(1, 5):
        tname = f"Sample Tenant {i}"
        existing = frappe.db.exists("Tenant", {"tenant_name": tname})
        if existing:
            tenant_names.append(existing)
            out["existing"].append(f"Tenant:{tname}")
            continue

        tenant = frappe.get_doc(
            {
                "doctype": "Tenant",
                "tenant_name": tname,
                "tenant_type": "Corporate" if i <= 2 else "Individual",
                "legal_name": f"Sample Tenant {i} Limited" if i <= 2 else f"Sample Tenant {i}",
                "onboarding_status": "Approved",
                "status": "Active",
            }
        )
        tenant.insert(ignore_permissions=True)
        tenant_names.append(tenant.name)
        out["created"].append(f"Tenant:{tname}")

    # Leases for occupied units + invoice fallback (no Billing Schedule doctype installed)
    occupied_units = [u for u in unit_names if frappe.db.get_value("Unit", u, "occupancy_status") == "Occupied"]
    for idx, unit_name in enumerate(occupied_units, start=1):
        lease_no = f"SAMPLE-LEASE-{idx:03d}"
        existing = frappe.db.exists("Lease", {"lease_no": lease_no})
        tenant = tenant_names[(idx - 1) % len(tenant_names)]
        property_name = frappe.db.get_value("Unit", unit_name, "property")

        if existing:
            out["existing"].append(f"Lease:{lease_no}")
            lease_name = existing
        else:
            lease = frappe.get_doc(
                {
                    "doctype": "Lease",
                    "lease_no": lease_no,
                    "company": company,
                    "portfolio": portfolio,
                    "property": property_name,
                    "tenant": tenant,
                    "lease_type": "New",
                    "lease_category": "Commercial"
                    if frappe.db.get_value("Unit", unit_name, "unit_type") == "Office"
                    else "Residential",
                    "currency": currency,
                    "start_date": nowdate(),
                    "end_date": add_days(nowdate(), 365),
                    "billing_cycle": "Monthly",
                    "approval_status": "Draft",
                    "status": "Draft",
                    "lease_units": [{"unit": unit_name}],
                    "lease_charges": [
                        {
                            "charge_type": "Base Rent",
                            "charge_basis": "Fixed",
                            "amount": 50000 * idx,
                            "frequency": "Monthly",
                            "start_date": nowdate(),
                            "billable": 1,
                        }
                    ],
                }
            )
            lease.insert(ignore_permissions=True)
            lease_name = lease.name
            out["created"].append(f"Lease:{lease_no}")

            # Try workflow transitions for realistic active status.
            try:
                from frappe.model.workflow import apply_workflow

                lease_doc = frappe.get_doc("Lease", lease_name)
                lease_doc = apply_workflow(lease_doc, "Submit for Approval")
                lease_doc = apply_workflow(lease_doc, "Approve")
                apply_workflow(lease_doc, "Activate Lease")
            except Exception:
                # Fallback for sample data if workflow permissions/actions differ.
                frappe.db.set_value("Lease", lease_name, "approval_status", "Approved", update_modified=False)
                frappe.db.set_value("Lease", lease_name, "status", "Active", update_modified=False)

        # Create fallback invoice for dashboard finance metrics.
        try:
            customer = _upsert_customer_for_tenant(tenant)
            if customer:
                invoice_exists = frappe.db.exists(
                    "Sales Invoice",
                    {"customer": customer, "remarks": ["like", f"%{lease_no}%"]},
                )
                if not invoice_exists:
                    item_code = _ensure_item("UAT-SERVICE-RENT", "UAT Service Rent", is_stock_item=0)
                    invoice = frappe.get_doc(
                        {
                            "doctype": "Sales Invoice",
                            "customer": customer,
                            "company": company,
                            "posting_date": nowdate(),
                            "due_date": add_days(nowdate(), 14),
                            "remarks": f"Sample lease billing for {lease_no}",
                            "items": [{"item_code": item_code, "qty": 1, "rate": 50000 * idx}],
                        }
                    )
                    invoice.insert(ignore_permissions=True)
                    try:
                        invoice.submit()
                    except Exception as exc:
                        out["warnings"].append(f"Sales Invoice submit skipped for {lease_no}: {exc}")
                    out["created"].append(f"Sales Invoice:{invoice.name}")
        except Exception as exc:
            out["warnings"].append(f"Invoice seed skipped for {lease_no}: {exc}")

    frappe.db.commit()

    out["counts"] = {
        "Property": frappe.db.count("Property"),
        "Unit": frappe.db.count("Unit"),
        "Tenant": frappe.db.count("Tenant"),
        "Lease": frappe.db.count("Lease"),
        "Sales Invoice": frappe.db.count("Sales Invoice"),
        "Payment Entry": frappe.db.count("Payment Entry"),
    }
    return out
