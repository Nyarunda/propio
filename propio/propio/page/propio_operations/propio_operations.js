frappe.pages["propio-operations"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("Propio Operations"),
    single_column: true,
  });

  const $body = $(
    `<div class="propio-ops p-3">
      <p class="text-muted mb-3">${__("Run scheduled jobs manually for operational control and testing.")}</p>
      <div class="alert alert-warning" role="alert">
        ${__("Use with care in production. These actions execute immediately.")}
      </div>
      <div class="mt-3" id="propio-ops-result"></div>
    </div>`
  ).appendTo(page.body);

  const resultEl = $body.find("#propio-ops-result");

  function renderResult(title, data, indicator) {
    const safe = frappe.utils.escape_html(JSON.stringify(data || {}, null, 2));
    resultEl.html(
      `<div class="mt-3">
        <div><strong>${frappe.utils.escape_html(title)}</strong></div>
        <pre class="mt-2 p-2" style="background:#f7f7f7;border:1px solid #e5e5e5;">${safe}</pre>
      </div>`
    );

    frappe.show_alert({ message: title, indicator: indicator || "green" }, 6);
  }

  function runTask(label, method) {
    frappe.confirm(
      __("Run {0} now?", [label]),
      () => {
        frappe.call({
          method,
          freeze: true,
          freeze_message: __("Running {0}...", [label]),
          callback: (r) => {
            renderResult(__("{0} completed", [label]), r.message || {}, "green");
          },
          error: () => {
            renderResult(__("{0} failed", [label]), { error: __("Check error logs") }, "red");
          },
        });
      }
    );
  }

  page.add_inner_button(__("Run Daily Tasks"), () => {
    runTask(__("Daily Tasks"), "propio.api.scheduled_tasks.trigger_daily_tasks");
  });

  page.add_inner_button(__("Run Weekly Tasks"), () => {
    runTask(__("Weekly Tasks"), "propio.api.scheduled_tasks.trigger_weekly_tasks");
  });

  page.add_inner_button(__("Run Monthly Tasks"), () => {
    runTask(__("Monthly Tasks"), "propio.api.scheduled_tasks.trigger_monthly_tasks");
  });

  page.set_primary_action(__("Open Error Log"), () => {
    frappe.set_route("List", "Error Log");
  });
};
