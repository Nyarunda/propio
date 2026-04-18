from __future__ import unicode_literals

import re

import frappe
from frappe import _
from frappe.core.doctype.user.user import reset_password as frappe_reset_password
from frappe.utils import add_to_date, get_url, now_datetime, sha256_hash
from frappe.utils.password import update_password as set_user_password


def _redirect_to_login():
    # Set both redirect flags to support website and API contexts.
    frappe.flags.redirect_location = "/login"
    frappe.local.response["location"] = "/login"


def _has_column(doctype_name, fieldname):
    return frappe.db.has_column(doctype_name, fieldname)


def _match_by_fields(doctype_name, user, candidate_fields):
    filters = {}
    for fieldname in candidate_fields:
        if _has_column(doctype_name, fieldname):
            filters[fieldname] = user
            name = frappe.db.get_value(doctype_name, filters, "name")
            if name:
                return name
            filters = {}
    return None


def _match_by_user_permission(doctype_name, user):
    if not frappe.db.exists("DocType", "User Permission"):
        return None

    return frappe.db.get_value(
        "User Permission",
        {
            "user": user,
            "allow": doctype_name,
            "applicable_for": ["in", ["", None]],
        },
        "for_value",
    ) or frappe.db.get_value(
        "User Permission",
        {"user": user, "allow": doctype_name},
        "for_value",
    )


def get_tenant_for_user(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return None

    tenant = _match_by_fields("Tenant", user, ["user", "portal_user", "email", "tenant_email"])
    if tenant:
        return tenant

    # Fallback: match by tenant contact email (child table) when tenant has no direct user/email field.
    if frappe.db.exists("DocType", "Tenant Contact"):
        tenant = frappe.db.get_value(
            "Tenant Contact",
            {"email": user, "parenttype": "Tenant"},
            "parent",
            order_by="is_primary desc, idx asc",
        )
        if tenant:
            return tenant

    return _match_by_user_permission("Tenant", user)


def get_owner_for_user(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return None

    owner = _match_by_fields("Owner", user, ["user", "portal_user", "email", "owner_email"])
    if owner:
        return owner

    return _match_by_user_permission("Owner", user)


def get_user_type(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return "guest"
    if get_tenant_for_user(user):
        return "tenant"
    if get_owner_for_user(user):
        return "owner"
    return "unknown"


def _coerce_user_to_website_user(user):
    if not user or user == "Guest" or not frappe.db.exists("User", user):
        return False

    user_type = frappe.db.get_value("User", user, "user_type")
    if user_type == "Website User":
        return False

    frappe.db.set_value("User", user, "user_type", "Website User", update_modified=False)
    return True


def _primary_tenant_contact_email(tenant_name):
    if not frappe.db.exists("DocType", "Tenant Contact"):
        return None

    return frappe.db.get_value(
        "Tenant Contact",
        {"parent": tenant_name, "parenttype": "Tenant"},
        "email",
        order_by="is_primary desc, idx asc",
    )


def _upsert_tenant_primary_contact(tenant_name, full_name, email, phone=None):
    if not frappe.db.exists("DocType", "Tenant Contact"):
        return

    existing = frappe.db.get_value(
        "Tenant Contact",
        {"parent": tenant_name, "parenttype": "Tenant", "email": email},
        "name",
    )

    if existing:
        if phone and frappe.db.has_column("Tenant Contact", "phone"):
            frappe.db.set_value("Tenant Contact", existing, "phone", phone, update_modified=False)
        return

    tenant = frappe.get_doc("Tenant", tenant_name)
    tenant.append(
        "tenant_contacts",
        {
            "contact_name": full_name or "Primary Contact",
            "role": "Primary",
            "email": email,
            "phone": phone,
            "is_primary": 1,
        },
    )
    tenant.save(ignore_permissions=True)


def _resolve_tenant_from_unit_code(unit_code):
    if not unit_code:
        return None
    if not frappe.db.exists("DocType", "Unit"):
        return None

    unit_name = frappe.db.get_value("Unit", {"unit_code": unit_code}, "name")
    if not unit_name:
        return None
    if not frappe.db.exists("DocType", "Lease Unit"):
        return None

    lease_name = frappe.db.get_value("Lease Unit", {"unit": unit_name}, "parent", order_by="creation desc")
    if not lease_name:
        return None
    return frappe.db.get_value("Lease", lease_name, "tenant")


def _create_tenant_from_signup(full_name, email, phone=None):
    tenant = frappe.get_doc(
        {
            "doctype": "Tenant",
            "tenant_name": full_name or email,
            "tenant_type": "Individual",
            "onboarding_status": "Pending Review",
            "status": "Active",
            "portal_enabled": 1 if frappe.db.has_column("Tenant", "portal_enabled") else 0,
        }
    )
    if frappe.db.exists("DocType", "Tenant Contact"):
        tenant.append(
            "tenant_contacts",
            {
                "contact_name": full_name or email,
                "role": "Primary",
                "email": email,
                "phone": phone,
                "is_primary": 1,
            },
        )

    tenant.insert(ignore_permissions=True)
    return tenant.name


def _ensure_user_permission_link(user, tenant_name):
    if not frappe.db.exists("DocType", "User Permission"):
        return None

    existing = frappe.db.exists(
        "User Permission",
        {"user": user, "allow": "Tenant", "for_value": tenant_name},
    )
    if existing:
        return existing

    doc = frappe.get_doc(
        {
            "doctype": "User Permission",
            "user": user,
            "allow": "Tenant",
            "for_value": tenant_name,
            "is_default": 1,
            "hide_descendants": 0,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _set_tenant_link_fields(tenant_name, user):
    if frappe.db.has_column("Tenant", "user"):
        frappe.db.set_value("Tenant", tenant_name, "user", user, update_modified=False)
    if frappe.db.has_column("Tenant", "portal_user"):
        frappe.db.set_value("Tenant", tenant_name, "portal_user", user, update_modified=False)


def _set_portal_home_for_user(user):
    user_type = get_user_type(user)
    if user_type == "tenant":
        target = "/tenant-portal"
    elif user_type == "owner":
        target = "/owner-portal"
    else:
        return

    frappe.local.response["home_page"] = target
    frappe.local.response["redirect_to"] = target


def _user_has_role(user, role_name):
    if not user or not role_name:
        return False
    return bool(frappe.db.exists("Has Role", {"parent": user, "role": role_name}))


def _is_valid_email(email):
    if not email:
        return False
    return bool(re.match(r"^[^\s@]+@([^\s@.,]+\.)+[^\s@.,]{2,}$", email))


def _send_portal_password_reset_email(email, full_name, reset_key):
    reset_url = get_url(f"/tenant-portal#/reset-password?key={reset_key}")
    display_name = full_name or email

    message = f"""
    <p>Hello {frappe.utils.escape_html(display_name)},</p>
    <p>We received a request to reset your Propio tenant portal password.</p>
    <p>
      <a href="{reset_url}">Reset Password</a>
    </p>
    <p>This link expires in 24 hours. If you did not request this, you can ignore this email.</p>
    <p>Reset URL: {reset_url}</p>
    """

    frappe.sendmail(
        recipients=[email],
        subject=_("Reset Your Propio Tenant Portal Password"),
        message=message,
        delayed=False,
    )


def _send_password_changed_confirmation(email, full_name):
    display_name = full_name or email
    message = f"""
    <p>Hello {frappe.utils.escape_html(display_name)},</p>
    <p>Your Propio tenant portal password was changed successfully.</p>
    <p>If this was not you, please contact your property manager immediately.</p>
    """
    frappe.sendmail(
        recipients=[email],
        subject=_("Your Propio Password Has Been Changed"),
        message=message,
        delayed=False,
    )


@frappe.whitelist(allow_guest=True)
def get_csrf_token():
    """
    Return the active session CSRF token for portal requests.
    """
    return {"success": True, "csrf_token": frappe.sessions.get_csrf_token()}


def require_portal_user(portal_type):
    if frappe.session.user == "Guest":
        _redirect_to_login()
        return None

    if portal_type == "tenant":
        tenant = get_tenant_for_user(frappe.session.user)
        if not tenant:
            _redirect_to_login()
        return tenant

    if portal_type == "owner":
        owner = get_owner_for_user(frappe.session.user)
        if not owner:
            _redirect_to_login()
        return owner

    return None


def enforce_portal_login_policy(login_manager=None):
    """
    Hook for on_session_creation:
    - Portal users (tenant/owner) are always Website Users (no ERP Desk access).
    - Their post-login landing page is forced to the correct portal.
    """
    lm = login_manager or getattr(frappe.local, "login_manager", None)
    user = getattr(lm, "user", None) or frappe.session.user
    if not user or user == "Guest":
        return

    user_type = get_user_type(user)
    if user_type not in {"tenant", "owner"}:
        return

    changed = _coerce_user_to_website_user(user)
    if lm and getattr(lm, "info", None):
        lm.info.user_type = "Website User"
        lm.user_type = "Website User"

    _set_portal_home_for_user(user)
    if changed:
        frappe.db.commit()


def redirect_portal_users_from_desk():
    """
    Server-side guard:
    If a tenant/owner portal user hits /desk directly, redirect to portal.
    """
    request = getattr(frappe.local, "request", None)
    if not request:
        return

    path = (getattr(request, "path", "") or "").strip()
    if not path.startswith("/desk"):
        return

    # Allow guests to use desk login flow.
    user = frappe.session.user
    if not user or user == "Guest":
        return

    user_type = get_user_type(user)
    if user_type == "tenant":
        target = "/tenant-portal"
    elif user_type == "owner":
        target = "/owner-portal"
    else:
        return

    frappe.local.flags.redirect_location = target
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = target
    frappe.local.response["http_status_code"] = 302


@frappe.whitelist(allow_guest=True)
def portal_login(email=None, password=None):
    email = email or frappe.form_dict.get("email")
    password = password or frappe.form_dict.get("password")

    try:
        if email:
            email = email.strip()
        if not email or not password:
            return {"success": False, "message": _("Email and password are required.")}
        if not _is_valid_email(email):
            return {"success": False, "message": _("Please enter a valid email address.")}

        frappe.local.login_manager.authenticate(email, password)
        frappe.local.login_manager.post_login()

        if not frappe.db.exists("User", email):
            frappe.local.login_manager.logout()
            return {"success": False, "message": _("Account not found.")}

        enabled = frappe.db.get_value("User", email, "enabled")
        if not int(enabled or 0):
            frappe.local.login_manager.logout()
            return {
                "success": False,
                "message": _("Account is disabled. Please contact your property manager."),
            }

        # Tenant portal is manager-provisioned only:
        # user must be mapped to a tenant and (if role exists) carry Tenant Portal User.
        tenant = get_tenant_for_user(email)
        if not tenant:
            frappe.local.login_manager.logout()
            return {
                "success": False,
                "message": _("No tenant record is linked to this account. Contact your property manager."),
            }

        if frappe.db.exists("Role", "Tenant Portal User") and not _user_has_role(email, "Tenant Portal User"):
            frappe.local.login_manager.logout()
            return {
                "success": False,
                "message": _("This account does not have tenant portal access. Contact your property manager."),
            }

        _set_portal_home_for_user(email)
        frappe.db.set_value("User", email, "last_login", frappe.utils.now(), update_modified=False)
        frappe.db.commit()
        return {"success": True, "user_type": "tenant", "redirect": "/tenant-portal", "tenant": tenant}
    except frappe.AuthenticationError:
        frappe.clear_messages()
        return {"success": False, "message": _("Invalid email or password.")}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Portal Login Error")
        frappe.clear_messages()
        return {"success": False, "message": _("Login failed. Please try again.")}


@frappe.whitelist(allow_guest=True)
def portal_request_password_reset(email=None):
    """
    Request a password reset email for tenant portal users.
    Returns a generic success response to avoid account enumeration.
    """
    email = (email or frappe.form_dict.get("email") or "").strip()
    if not _is_valid_email(email):
        return {"success": False, "message": _("Please enter a valid email address.")}

    generic_message = _(
        "If an eligible account exists for this email, password reset instructions will be sent."
    )

    try:
        # Portal policy: only manager-provisioned tenant accounts are eligible.
        tenant = get_tenant_for_user(email)
        if not tenant:
            return {"success": True, "message": generic_message}

        if frappe.db.exists("Role", "Tenant Portal User") and not _user_has_role(email, "Tenant Portal User"):
            return {"success": True, "message": generic_message}

        enabled = frappe.db.get_value("User", email, "enabled")
        if not int(enabled or 0):
            return {"success": True, "message": generic_message}

        frappe_reset_password(user=email)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Portal Password Reset Request Error")

    return {"success": True, "message": generic_message}


@frappe.whitelist(allow_guest=True)
def forgot_password(email=None):
    """
    Public tenant-portal forgot password endpoint.
    Sends a tenant-portal reset link when eligible.
    """
    email = (email or frappe.form_dict.get("email") or "").strip()
    if not _is_valid_email(email):
        return {"success": False, "message": _("Please enter a valid email address.")}

    generic_message = _(
        "If an eligible account exists for this email, password reset instructions will be sent."
    )

    try:
        if not frappe.db.exists("User", email):
            return {"success": True, "message": generic_message}

        tenant = get_tenant_for_user(email)
        if not tenant:
            return {"success": True, "message": generic_message}

        if frappe.db.exists("Role", "Tenant Portal User") and not _user_has_role(email, "Tenant Portal User"):
            return {"success": True, "message": generic_message}

        enabled = frappe.db.get_value("User", email, "enabled")
        if not int(enabled or 0):
            return {"success": True, "message": generic_message}

        reset_key = frappe.generate_hash(length=32)
        frappe.db.set_value("User", email, "reset_password_key", sha256_hash(reset_key), update_modified=False)
        frappe.db.set_value("User", email, "last_reset_password_key_generated_on", now_datetime(), update_modified=False)

        full_name = frappe.db.get_value("User", email, "full_name")
        _send_portal_password_reset_email(email, full_name, reset_key)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Tenant Forgot Password Error")

    return {"success": True, "message": generic_message}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def reset_password(key=None, new_password=None, confirm_password=None):
    """
    Complete password reset using key from email link.
    """
    key = (key or frappe.form_dict.get("key") or "").strip()
    new_password = new_password or frappe.form_dict.get("new_password")
    confirm_password = confirm_password or frappe.form_dict.get("confirm_password")

    if not key:
        return {"success": False, "message": _("Invalid or expired reset link.")}
    if not new_password or not confirm_password:
        return {"success": False, "message": _("Both password fields are required.")}
    if new_password != confirm_password:
        return {"success": False, "message": _("Passwords do not match.")}
    if len(new_password) < 6:
        return {"success": False, "message": _("Password must be at least 6 characters.")}

    try:
        hashed_key = sha256_hash(key)
        user = frappe.db.get_value(
            "User",
            {"reset_password_key": hashed_key, "enabled": 1},
            ["name", "last_reset_password_key_generated_on", "full_name"],
            as_dict=True,
        )
        if not user:
            return {"success": False, "message": _("Invalid or expired reset link.")}

        # Match Frappe semantics: expiry value is in seconds.
        expiry_seconds = frappe.utils.cint(frappe.get_system_settings("reset_password_link_expiry_duration")) or 86400
        generated_on = user.last_reset_password_key_generated_on
        if generated_on and now_datetime() > add_to_date(generated_on, seconds=expiry_seconds):
            return {"success": False, "message": _("Reset link has expired. Please request a new one.")}

        set_user_password(user.name, new_password, logout_all_sessions=True)
        frappe.db.set_value("User", user.name, "reset_password_key", "", update_modified=False)
        frappe.db.set_value("User", user.name, "last_reset_password_key_generated_on", None, update_modified=False)
        frappe.db.set_value("User", user.name, "last_password_reset_date", frappe.utils.today(), update_modified=False)

        _send_password_changed_confirmation(user.name, user.full_name)
        frappe.db.commit()
        return {
            "success": True,
            "message": _("Password has been reset successfully. You can now sign in with your new password."),
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Tenant Reset Password Error")
        return {"success": False, "message": _("Failed to reset password. Please try again.")}


@frappe.whitelist(methods=["POST"])
def change_password(current_password=None, new_password=None, confirm_password=None):
    """
    Change password for currently logged-in tenant user.
    """
    user = frappe.session.user
    if user == "Guest":
        return {"success": False, "message": _("You must be logged in to change password.")}

    current_password = current_password or frappe.form_dict.get("current_password")
    new_password = new_password or frappe.form_dict.get("new_password")
    confirm_password = confirm_password or frappe.form_dict.get("confirm_password")

    if not current_password or not new_password or not confirm_password:
        return {"success": False, "message": _("All fields are required.")}
    if new_password != confirm_password:
        return {"success": False, "message": _("New passwords do not match.")}
    if len(new_password) < 6:
        return {"success": False, "message": _("Password must be at least 6 characters.")}
    if current_password == new_password:
        return {"success": False, "message": _("New password must be different from current password.")}

    try:
        frappe.local.login_manager.check_password(user, current_password)
    except Exception:
        return {"success": False, "message": _("Current password is incorrect.")}

    try:
        set_user_password(user, new_password, logout_all_sessions=False)
        frappe.db.set_value("User", user, "last_password_reset_date", frappe.utils.today(), update_modified=False)
        frappe.db.commit()
        return {"success": True, "message": _("Password changed successfully.")}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Tenant Change Password Error")
        return {"success": False, "message": _("Failed to change password. Please try again.")}


@frappe.whitelist(allow_guest=True)
def portal_register_tenant(
    tenant=None,
    email=None,
    full_name=None,
    password=None,
    tenant_ref=None,
    phone=None,
    unit_code=None,
):
    """
    Tenant self-registration is intentionally disabled.
    Tenants must be provisioned by property/lease managers.
    """
    return {
        "success": False,
        "status": "disabled",
        "message": _("Self-registration is disabled. Please contact your property or lease manager."),
    }


@frappe.whitelist()
def ensure_tenant_portal_access(tenant, email=None, full_name=None, password=None, send_welcome_email=0):
    """
    Admin/ERP flow:
    Ensure a tenant has a portal-capable user that can only use the portal.
    """
    if not tenant:
        frappe.throw(_("Tenant is required"))
    if not frappe.db.exists("Tenant", tenant):
        frappe.throw(_("Tenant {0} was not found").format(tenant))

    email = email or _primary_tenant_contact_email(tenant)
    if not email:
        frappe.throw(_("No email found. Provide email or set a primary Tenant Contact email."))

    user = frappe.db.exists("User", email)
    if not user:
        doc = frappe.new_doc("User")
        doc.email = email
        doc.first_name = full_name or frappe.db.get_value("Tenant", tenant, "tenant_name") or "Tenant"
        doc.enabled = 1
        doc.user_type = "Website User"
        doc.send_welcome_email = int(send_welcome_email or 0)
        if password:
            doc.new_password = password
        doc.insert(ignore_permissions=True)
        user = doc.name
    else:
        _coerce_user_to_website_user(user)
        frappe.db.set_value("User", user, "enabled", 1, update_modified=False)

    _set_tenant_link_fields(tenant, user)
    if frappe.db.has_column("Tenant", "portal_enabled"):
        frappe.db.set_value("Tenant", tenant, "portal_enabled", 1, update_modified=False)
    _ensure_user_permission_link(user, tenant)
    frappe.db.commit()

    return {
        "success": True,
        "tenant": tenant,
        "user": user,
        "portal": "/tenant-portal",
        "message": _("Tenant portal access is ready"),
    }


@frappe.whitelist()
def get_tenant_portal_status():
    user = frappe.session.user
    if not user or user == "Guest":
        return {"is_portal_user": False, "portal_type": None, "redirect": "/tenant-portal#/login"}

    user_type = get_user_type(user)
    if user_type == "tenant":
        return {"is_portal_user": True, "portal_type": "tenant", "redirect": "/tenant-portal"}
    if user_type == "owner":
        return {"is_portal_user": True, "portal_type": "owner", "redirect": "/owner-portal"}

    return {"is_portal_user": False, "portal_type": None, "redirect": None}


@frappe.whitelist(allow_guest=True)
def portal_logout():
    if frappe.session.user == "Guest":
        return {"success": True}

    frappe.local.login_manager.logout()
    return {"success": True}


@frappe.whitelist(allow_guest=True)
def logout():
    """Compatibility alias for SPA logout calls."""
    try:
        res = portal_logout()
        if isinstance(res, dict):
            res.setdefault("redirect", "/tenant-portal#/login")
        return res
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Portal Logout Error")
        return {"success": False, "message": _("Logout failed.")}


@frappe.whitelist(allow_guest=True)
def check_session():
    """
    Return tenant-portal auth state.
    Only returns logged_in=True for tenant portal users linked to a tenant.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return {"logged_in": False}

    tenant = get_tenant_for_user(user)
    if not tenant:
        return {"logged_in": False}

    if frappe.db.exists("Role", "Tenant Portal User") and not _user_has_role(user, "Tenant Portal User"):
        return {"logged_in": False}

    return {
        "logged_in": True,
        "user": user,
        "tenant": tenant,
        "full_name": frappe.db.get_value("User", user, "full_name"),
        "user_image": frappe.db.get_value("User", user, "user_image"),
    }


@frappe.whitelist(allow_guest=True)
def get_current_user():
    if frappe.session.user == "Guest":
        return {"logged_in": False}

    user_type = get_user_type(frappe.session.user)
    return {
        "logged_in": True,
        "user": frappe.session.user,
        "full_name": frappe.db.get_value("User", frappe.session.user, "full_name"),
        "user_type": user_type,
        "tenant": get_tenant_for_user(frappe.session.user),
        "owner": get_owner_for_user(frappe.session.user),
    }
