(() => {
  // ../propio/propio/public/js/app/main.bundle.js
  (function() {
    "use strict";
    (function() {
      function r(n) {
        if (!n || !n.querySelectorAll)
          return;
        const t = "/assets/frappe/images/ui/avatar.png";
        n.querySelectorAll('img[src="undefined"], img[src="/undefined"], img[src*="/undefined?"]').forEach((e) => {
          e.dataset.propioFixedSrc !== "1" && (e.dataset.propioFixedSrc = "1", e.src = t);
        });
      }
      function o() {
        r(document), new MutationObserver((t) => {
          for (const e of t)
            for (const d of e.addedNodes)
              d.nodeType === 1 && r(d);
        }).observe(document.documentElement, { childList: true, subtree: true }), window.addEventListener("error", (t) => {
          const e = t.target;
          e && e.tagName === "IMG" && (e.getAttribute("src") || "").includes("undefined") && (e.src = "/assets/frappe/images/ui/avatar.png");
        }, true);
      }
      document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", o, { once: true }) : o(), window.frappe && console.log("Propio app bundle loaded");
    })();
  })();
})();
//# sourceMappingURL=main.bundle.NGLHRI62.js.map
