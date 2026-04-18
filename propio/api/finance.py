import frappe


@frappe.whitelist()
def finance_health_snapshot():
    return {"message": "Finance API ready"}
