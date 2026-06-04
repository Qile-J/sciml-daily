(function () {
  var papers = [].slice.call(document.querySelectorAll(".paper"));
  var pills = [].slice.call(document.querySelectorAll(".pill"));
  var search = document.getElementById("search");
  var counter = document.getElementById("visible-count");
  var empty = document.getElementById("empty");
  var activeTag = "";

  // per-tag counts on the pills; hide tags absent today
  var counts = {};
  papers.forEach(function (el) {
    (el.dataset.tags || "").split(" ").filter(Boolean).forEach(function (t) {
      counts[t] = (counts[t] || 0) + 1;
    });
  });
  pills.forEach(function (pill) {
    var t = pill.dataset.tag;
    var n = t ? counts[t] : papers.length;
    if (n) {
      var s = document.createElement("span");
      s.className = "n"; s.textContent = n; pill.appendChild(s);
    } else if (t) {
      pill.style.display = "none";
    }
  });

  function apply() {
    var q = (search && search.value || "").trim().toLowerCase();
    var shown = 0;
    papers.forEach(function (el) {
      var okTag = !activeTag || (el.dataset.tags || "").split(" ").indexOf(activeTag) !== -1;
      var okText = !q || (el.dataset.text || "").indexOf(q) !== -1;
      var vis = okTag && okText;
      el.style.display = vis ? "" : "none";
      if (vis) shown++;
    });
    if (counter) counter.textContent = shown;
    if (empty) empty.hidden = shown !== 0;
  }

  pills.forEach(function (pill) {
    pill.addEventListener("click", function () {
      activeTag = pill.dataset.tag;
      pills.forEach(function (p) { p.classList.remove("active"); });
      pill.classList.add("active");
      apply();
    });
  });
  if (search) search.addEventListener("input", apply);

  document.querySelectorAll(".abstract-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var ab = btn.closest(".paper").querySelector(".abstract");
      var open = !ab.hidden;
      ab.hidden = open;
      btn.setAttribute("aria-expanded", String(!open));
      btn.textContent = open ? "Abstract" : "Hide abstract";
    });
  });
})();
