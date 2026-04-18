frappe.query_reports["Aging Report"] = {
  filters: [
    {
      fieldname: "property",
      label: __("Property"),
      fieldtype: "Link",
      options: "Property"
    },
    {
      fieldname: "tenant",
      label: __("Tenant"),
      fieldtype: "Link",
      options: "Tenant"
    },
    {
      fieldname: "days_overdue_min",
      label: __("Min Days Overdue"),
      fieldtype: "Int"
    },
    {
      fieldname: "days_overdue_max",
      label: __("Max Days Overdue"),
      fieldtype: "Int"
    }
  ]
};
