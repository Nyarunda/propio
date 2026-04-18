from __future__ import unicode_literals

import frappe


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = 0
    context.title = "Tenant Portal"
    # Force fresh SPA asset URLs so browser does not keep stale bundles.
    context.build_version = frappe.utils.now_datetime().strftime("%Y%m%d%H%M%S")
