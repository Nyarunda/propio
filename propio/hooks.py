from __future__ import unicode_literals

app_name = "propio"
app_title = "Propio"
app_publisher = "Your Company"
app_description = "Enterprise Property Management Platform"
app_email = "support@propio.com"
app_license = "gpl-3.0"

required_apps = ["erpnext"]

fixtures = [
    "Role",
    "Workspace",
    "Number Card",
    "Dashboard Chart",
    "Report",
    "Workflow",
]

app_include_js = ["main.bundle.js"]

doctype_js = {
    "Tenant": "public/js/tenant.js",
}

override_doctype_class = {
    "Notification": "propio.overrides.notification.CustomNotification",
}

doc_events = {
    "Lease": {
        "on_update": "propio.api.leasing.sync_occupancy",
        "validate": "propio.api.leasing.validate_lease",
    },
    "Service Request": {
        "on_update": "propio.api.maintenance.check_sla",
    },
    "Payment Intake": {
        "on_update": "propio.api.collections.auto_match_payment",
    },
}

scheduler_events = {
    "daily": [
        "propio.api.scheduled_tasks.daily_arrears_case_creation",
        "propio.api.scheduled_tasks.update_expiring_leases",
        "propio.api.scheduled_tasks.cleanup_old_notifications",
        "propio.api.notifications.send_expiry_alerts",
        "propio.api.collections.update_arrears_cases",
    ],
    "weekly": [
        "propio.api.scheduled_tasks.weekly_owner_statement_generation",
    ],
    "monthly": [
        "propio.api.scheduled_tasks.monthly_fee_calculation",
    ],
    "hourly": [
        "propio.api.scheduled_tasks.send_overdue_notifications",
        "propio.api.maintenance.update_overdue_work_orders",
    ],
}

permission_query_conditions = {
    "Property": "propio.api.permission.get_property_conditions",
    "Lease": "propio.api.permission.get_lease_conditions",
    "Unit": "propio.api.permission.get_unit_conditions",
}

has_permission = {
    "Property": "propio.api.permission.has_property_permission",
}

custom_fields = {}

website_route_rules = [
    {"from_route": "/tenant-portal", "to_route": "tenant-portal"},
    {"from_route": "/owner-portal", "to_route": "owner-portal"},
]

on_session_creation = [
    "propio.portal_utils.auth.enforce_portal_login_policy",
]

before_request = [
    "propio.portal_utils.auth.redirect_portal_users_from_desk",
]
