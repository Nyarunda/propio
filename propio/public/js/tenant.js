frappe.ui.form.on("Tenant", {
  refresh(frm) {
    if (frm.is_new()) return;

    frm.add_custom_button(__("Grant Portal Access"), () => {
      frappe.call({
        method: "propio.portal_utils.tenant_provisioning.create_tenant_portal_access",
        args: {
          tenant_name: frm.doc.name,
          send_welcome_email: 1,
        },
        callback: (r) => {
          const msg = r?.message || {};
          frappe.msgprint({
            title: msg.status === "success" ? __("Portal Access Granted") : __("Portal Access"),
            indicator: msg.status === "success" ? "green" : "orange",
            message: __(msg.message || "Done"),
          });
        },
      });
    }, __("Portal"));

    frm.add_custom_button(__("Revoke Portal Access"), () => {
      frappe.call({
        method: "propio.portal_utils.tenant_provisioning.revoke_tenant_portal_access",
        args: {
          tenant_name: frm.doc.name,
        },
        callback: (r) => {
          const msg = r?.message || {};
          frappe.msgprint({
            title: msg.status === "success" ? __("Portal Access Revoked") : __("Portal Access"),
            indicator: msg.status === "success" ? "red" : "orange",
            message: __(msg.message || "Done"),
          });
        },
      });
    }, __("Portal"));
  },
});
