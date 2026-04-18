from __future__ import unicode_literals

import frappe
from frappe.utils.pdf import get_pdf

from propio.portal_utils.auth import get_owner_for_user


@frappe.whitelist()
def download_statement_pdf(statement):
    statement_doc = frappe.get_doc("Owner Statement", statement)
    owner = get_owner_for_user(frappe.session.user)

    if not owner or statement_doc.owner != owner:
        frappe.throw("Access denied")

    html = frappe.render_template(
        "propio/templates/portal/owner_statement_pdf.html",
        {
            "doc": statement_doc,
            "company": frappe.get_doc("Company", statement_doc.company),
        },
    )

    pdf = get_pdf(html)
    frappe.local.response.filename = f"Owner_Statement_{statement}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"
