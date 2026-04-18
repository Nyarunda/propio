from frappe import _


def get_data():
    return [
        {
            "module_name": "Property",
            "type": "module",
            "label": _("Property"),
            "icon": "building-2",
            "color": "blue",
        },
        {
            "module_name": "Leasing",
            "type": "module",
            "label": _("Leasing"),
            "icon": "file-text",
            "color": "cyan",
        },
        {
            "module_name": "Propio Maintenance",
            "type": "module",
            "label": _("Maintenance"),
            "icon": "wrench",
            "color": "orange",
        },
        {
            "module_name": "Finance",
            "type": "module",
            "label": _("Finance"),
            "icon": "wallet",
            "color": "green",
        },
        {
            "module_name": "Collections",
            "type": "module",
            "label": _("Collections"),
            "icon": "alert-triangle",
            "color": "red",
        },
        {
            "module_name": "Owner",
            "type": "module",
            "label": _("Owner"),
            "icon": "users",
            "color": "gray",
        },
    ]
