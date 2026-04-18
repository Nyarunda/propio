frappe.query_reports["Collections Performance Report"] = {
  filters: [
    {
      fieldname: "year",
      label: __("Year"),
      fieldtype: "Int",
      default: new Date().getFullYear()
    }
  ]
};
