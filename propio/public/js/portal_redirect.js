frappe.ready(() => {
  const path = window.location.pathname || "";
  if (!(path.startsWith("/app") || path.startsWith("/desk"))) return;
  if (!frappe.session || frappe.session.user === "Guest") return;

  frappe.call({
    method: "propio.portal_utils.auth.get_tenant_portal_status",
    callback: function (r) {
      const info = r && r.message;
      if (info && info.is_portal_user && info.redirect) {
        window.location.replace(info.redirect);
      }
    },
  });
});
