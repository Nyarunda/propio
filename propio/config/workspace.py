from frappe import _


def get_data():
    return [
        {
            "label": _("Property"),
            "icon": "building-2",
            "items": [
                {"type": "doctype", "name": "Property", "label": _("Property")},
                {"type": "doctype", "name": "Unit", "label": _("Unit")},
                {"type": "doctype", "name": "Lease", "label": _("Lease")},
            ],
        },
        {
            "label": _("Leasing"),
            "icon": "file-text",
            "items": [
                {"type": "doctype", "name": "Lease", "label": _("Lease")},
                {"type": "doctype", "name": "Tenant", "label": _("Tenant")},
            ],
        },
        {
            "label": _("Maintenance"),
            "icon": "wrench",
            "items": [
                {"type": "doctype", "name": "Service Request", "label": _("Service Request")},
                {"type": "doctype", "name": "Work Order", "label": _("Work Order")},
            ],
        },
        {
            "label": _("Finance"),
            "icon": "wallet",
            "items": [
                {"type": "doctype", "name": "Payment Intake", "label": _("Payment Intake")},
                {"type": "doctype", "name": "Owner Statement", "label": _("Owner Statement")},
            ],
        },
        {
            "label": _("Collections"),
            "icon": "alert-triangle",
            "items": [
                {"type": "doctype", "name": "Arrears Case", "label": _("Arrears Case")},
                {"type": "doctype", "name": "Collections Follow Up", "label": _("Collections Follow Up")},
            ],
        },
        {
            "label": _("Owner"),
            "icon": "users",
            "items": [
                {"type": "doctype", "name": "Owner Statement", "label": _("Owner Statement")},
                {"type": "doctype", "name": "Management Agreement", "label": _("Management Agreement")},
            ],
        }
    ]
