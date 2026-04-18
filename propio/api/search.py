import frappe


@frappe.whitelist()
def global_search(doctype: str, txt: str):
    return frappe.get_all(doctype, filters={"name": ["like", f"%{txt}%"]}, limit=20)
