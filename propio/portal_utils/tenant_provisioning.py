from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import get_url, random_string

from propio.portal_utils.auth import ensure_tenant_portal_access


def _tenant_primary_contact_email(tenant_name: str) -> str | None:
    if not frappe.db.exists("DocType", "Tenant Contact"):
        return None
    return frappe.db.get_value(
        "Tenant Contact",
        {"parent": tenant_name, "parenttype": "Tenant"},
        "email",
        order_by="is_primary desc, idx asc",
    )


def _tenant_display_name(tenant_name: str) -> str:
    return frappe.db.get_value("Tenant", tenant_name, "tenant_name") or tenant_name


def _ensure_role_on_user(user: str, role_name: str) -> None:
    if not frappe.db.exists("Role", role_name):
        return
    if frappe.db.exists("Has Role", {"parent": user, "role": role_name}):
        return
    user_doc = frappe.get_doc("User", user)
    user_doc.append("roles", {"role": role_name})
    user_doc.save(ignore_permissions=True)


def _send_tenant_welcome_email(email: str, tenant_name: str, temp_password: str | None = None) -> None:
    portal_url = get_url("/tenant-portal#/login")
    password_hint = (
        f"<p><strong>Temporary Password:</strong> <code>{temp_password}</code></p>"
        if temp_password
        else "<p>Your existing password is still active.</p>"
    )

    message = f"""
    <p>Hello {frappe.utils.escape_html(tenant_name)},</p>
    <p>Your tenant portal access is ready.</p>
    <p><strong>Portal URL:</strong> <a href="{portal_url}">{portal_url}</a><br>
    <strong>Email:</strong> {frappe.utils.escape_html(email)}</p>
    {password_hint}
    <p>If you have trouble logging in, please contact your property manager.</p>
    """

    frappe.sendmail(
        recipients=[email],
        subject=f"Tenant Portal Access - {tenant_name}",
        message=message,
        delayed=False,
    )


@frappe.whitelist()
def create_tenant_portal_access(tenant_name, email=None, send_welcome_email=True):
    """
    Provision portal access for an existing tenant (manager action).
    """
    if not frappe.db.exists("Tenant", tenant_name):
        return {"status": "error", "message": _("Tenant {0} not found").format(tenant_name)}

    tenant_label = _tenant_display_name(tenant_name)
    user_email = email or _tenant_primary_contact_email(tenant_name)
    if not user_email:
        return {
            "status": "error",
            "message": _("No tenant contact email found. Add a primary Tenant Contact email first."),
        }

    user_exists = bool(frappe.db.exists("User", user_email))
    temp_password = None if user_exists else random_string(10)

    result = ensure_tenant_portal_access(
        tenant=tenant_name,
        email=user_email,
        full_name=tenant_label,
        password=temp_password,
        send_welcome_email=0,
    )

    _ensure_role_on_user(user_email, "Tenant Portal User")

    send_mail = int(send_welcome_email or 0) == 1
    if send_mail:
        _send_tenant_welcome_email(user_email, tenant_label, temp_password=temp_password)

    return {
        "status": "success",
        "message": _("Portal access created for {0}").format(tenant_name),
        "email": user_email,
        "temporary_password": temp_password if (temp_password and not send_mail) else ("sent via email" if temp_password else None),
        "result": result,
    }


@frappe.whitelist()
def revoke_tenant_portal_access(tenant_name):
    """
    Disable tenant portal access by disabling the linked User account.
    """
    if not frappe.db.exists("Tenant", tenant_name):
        return {"status": "error", "message": _("Tenant {0} not found").format(tenant_name)}

    user = None
    if frappe.db.has_column("Tenant", "user"):
        user = frappe.db.get_value("Tenant", tenant_name, "user")
    if not user and frappe.db.has_column("Tenant", "portal_user"):
        user = frappe.db.get_value("Tenant", tenant_name, "portal_user")
    if not user:
        user = _tenant_primary_contact_email(tenant_name)

    if not user or not frappe.db.exists("User", user):
        return {"status": "error", "message": _("No linked user found for tenant {0}").format(tenant_name)}

    frappe.db.set_value("User", user, "enabled", 0, update_modified=False)
    frappe.db.commit()
    return {"status": "success", "message": _("Portal access revoked for {0}").format(tenant_name), "user": user}


def provision_all_tenants_with_email(send_welcome_email=False):
    """
    Utility for CLI bulk provisioning.
    """
    if not frappe.db.exists("DocType", "Tenant Contact"):
        return {"total": 0, "success": 0, "failed": 0, "rows": [], "message": "Tenant Contact doctype not found."}

    tenants = frappe.get_all("Tenant", pluck="name")
    rows = []
    success = 0
    failed = 0

    for tenant in tenants:
        email = _tenant_primary_contact_email(tenant)
        if not email:
            rows.append({"tenant": tenant, "status": "skipped", "message": "No primary email"})
            continue
        try:
            res = create_tenant_portal_access(tenant, email=email, send_welcome_email=send_welcome_email)
            rows.append({"tenant": tenant, "status": res.get("status"), "message": res.get("message")})
            if res.get("status") == "success":
                success += 1
            else:
                failed += 1
        except Exception as exc:
            failed += 1
            rows.append({"tenant": tenant, "status": "error", "message": str(exc)})

    return {"total": len(tenants), "success": success, "failed": failed, "rows": rows}
