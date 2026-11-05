// Theme toggle (remembered per viewer when storage is available) + action-library filters.
(function () {
  var root = document.documentElement;
  try {
    var saved = localStorage.getItem("rsae-theme");
    if (saved === "light" || saved === "dark") root.setAttribute("data-theme", saved);
  } catch (e) { /* storage unavailable: follow the OS setting */ }

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("theme-toggle");
    if (btn) {
      var label = function () {
        var dark = root.getAttribute("data-theme") === "dark" ||
          (!root.getAttribute("data-theme") && window.matchMedia("(prefers-color-scheme: dark)").matches);
        btn.textContent = dark ? "Light mode" : "Dark mode";
        return dark;
      };
      label();
      btn.addEventListener("click", function () {
        var next = label() ? "light" : "dark";
        root.setAttribute("data-theme", next);
        try { localStorage.setItem("rsae-theme", next); } catch (e) { /* ignore */ }
        label();
      });
    }

    var table = document.getElementById("library");
    if (!table) return;
    var controls = document.querySelectorAll("[data-filter]");
    var count = document.getElementById("library-count");
    var apply = function () {
      var shown = 0;
      table.querySelectorAll("tbody tr").forEach(function (tr) {
        var ok = true;
        controls.forEach(function (c) {
          var v = c.value.trim().toLowerCase();
          if (!v) return;
          var key = c.getAttribute("data-filter");
          var cell = (tr.getAttribute("data-" + key) || "").toLowerCase();
          if (key === "q") ok = ok && cell.indexOf(v) !== -1;
          else if (key === "stars") ok = ok && Number(tr.getAttribute("data-stars") || 0) >= Number(v);
          else ok = ok && cell.split("|").indexOf(v) !== -1;
        });
        tr.hidden = !ok;
        if (ok) shown++;
      });
      if (count) count.textContent = shown + " entries shown";
    };
    controls.forEach(function (c) { c.addEventListener("input", apply); });
    apply();
  });
})();
