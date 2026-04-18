frappe.query_reports["Owner Statement Register"] = {
  filters: [
    {
      fieldname: "owner",
      label: __("Owner"),
      fieldtype: "Link",
      options: "Owner"
    },
    {
      fieldname: "property",
      label: __("Property"),
      fieldtype: "Link",
      options: "Property"
    },
    {
      fieldname: "status",
      label: __("Status"),
      fieldtype: "Select",
      options: ["", "Draft", "Reviewed", "Approved", "Paid", "Closed"]
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date"
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date"
    }
  ]
};
