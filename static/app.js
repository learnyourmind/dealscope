// Progressive enhancement only: the form works without JavaScript.
(function () {
  var form = document.getElementById("analyze-form");
  if (!form) return;
  var button = document.getElementById("submit-btn");
  var status = document.getElementById("status");
  var label = button.textContent;

  form.addEventListener("submit", function (event) {
    if (form.dataset.busy === "1") {
      event.preventDefault(); // prevent accidental double submission
      return;
    }
    form.dataset.busy = "1";
    button.setAttribute("aria-disabled", "true");
    button.textContent = "Analyzing…";
    status.textContent = "Analyzing property. This can take a few seconds.";
  });

  // Restore state when returning via the back/forward cache.
  window.addEventListener("pageshow", function () {
    form.dataset.busy = "0";
    button.removeAttribute("aria-disabled");
    button.textContent = label;
    status.textContent = "";
  });

  // Move focus to the error summary or results so keyboard and screen-reader users land on them.
  var target = document.getElementById("error-summary") || document.getElementById("results-h");
  if (target) target.focus();
})();
