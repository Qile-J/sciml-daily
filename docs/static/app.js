(function () {
  "use strict";

  var TAGS = {}, PAPERS = [], DATES = [], byDate = {}, latest = null;
  var searchTags = {};

  function $(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function asDate(d) { var p = d.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function fmtFull(d) {
    return asDate(d).toLocaleDateString("en-US",
      { weekday: "long", year: "numeric", month: "long", day: "numeric" });
  }
  function fmtShort(d) {
    return asDate(d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }
  function plural(n) { return n + (n === 1 ? " paper" : " papers"); }

  function tagPill(slug) {
    var t = TAGS[slug];
    return t ? '<span class="tag" style="--c:' + t.color + '">' + esc(t.name) + "</span>" : "";
  }
  function accent(p) {
    var t = TAGS[(p.tags && p.tags[0]) || ""];
    return t ? t.color : "#94a3b8";
  }
  function delatex(s) {
    if (!s) return s;
    return s
      .replace(/\{?\\aa\}?/gi, 'å').replace(/\{?\\AA\}?/gi, 'Å')
      .replace(/\{?\\ae\}?/gi, 'æ').replace(/\{?\\AE\}?/gi, 'Æ')
      .replace(/\{?\\oe\}?/gi, 'œ').replace(/\{?\\OE\}?/gi, 'Œ')
      .replace(/\{?\\ss\}?/gi, 'ß')
      .replace(/\{?\\o\}?/g,   'ø').replace(/\{?\\O\}?/g,   'Ø')
      .replace(/\{?\\l\}?/g,   'ł').replace(/\{?\\L\}?/g,   'Ł')
      .replace(/\\"\{?([a-zA-Z])\}?/g, function(_, c) {
        return {a:'ä',e:'ë',i:'ï',o:'ö',u:'ü',y:'ÿ',
                A:'Ä',E:'Ë',I:'Ï',O:'Ö',U:'Ü',Y:'Ÿ'}[c] || c;
      })
      .replace(/\\'\{?([a-zA-Z])\}?/g, function(_, c) {
        return {a:'á',e:'é',i:'í',o:'ó',u:'ú',y:'ý',c:'ć',n:'ń',s:'ś',z:'ź',
                A:'Á',E:'É',I:'Í',O:'Ó',U:'Ú',Y:'Ý',C:'Ć',N:'Ń',S:'Ś',Z:'Ź'}[c] || c;
      })
      .replace(/\\`\{?([a-zA-Z])\}?/g, function(_, c) {
        return {a:'à',e:'è',i:'ì',o:'ò',u:'ù',A:'À',E:'È',I:'Ì',O:'Ò',U:'Ù'}[c] || c;
      })
      .replace(/\\~\{?([a-zA-Z])\}?/g, function(_, c) {
        return {n:'ñ',N:'Ñ',a:'ã',A:'Ã',o:'õ',O:'Õ'}[c] || c;
      })
      .replace(/\\\^\{?([a-zA-Z])\}?/g, function(_, c) {
        return {a:'â',e:'ê',i:'î',o:'ô',u:'û',A:'Â',E:'Ê',I:'Î',O:'Ô',U:'Û'}[c] || c;
      })
      .replace(/\\c\{?([a-zA-Z])\}?/g, function(_, c) {
        return {c:'ç',C:'Ç',s:'ş',S:'Ş'}[c] || c;
      })
      .replace(/\\v\{?([a-zA-Z])\}?/g, function(_, c) {
        return {c:'č',C:'Č',s:'š',S:'Š',z:'ž',Z:'Ž',n:'ň',N:'Ň',r:'ř',R:'Ř'}[c] || c;
      })
      .replace(/[{}]/g, '');
  }

  function authorsLine(a) {
    a = (a || []).map(delatex);
    return a.length <= 10
      ? esc(a.join(", "))
      : esc(a.slice(0, 10).join(", ")) + " +" + (a.length - 10);
  }

  var KATEX_OPTS = {
    delimiters: [
      {left: "$$", right: "$$", display: true},
      {left: "$",  right: "$",  display: false},
      {left: "\\(", right: "\\)", display: false},
      {left: "\\[", right: "\\]", display: true}
    ],
    throwOnError: false
  };

  function card(p, showDate) {
    var tags = (p.tags || []).map(tagPill).join("");
    var front = '<div class="card-front">'
      + '<h2><a href="' + esc(p.url) + '" target="_blank" rel="noopener">' + esc(p.title) + "</a></h2>"
      + (p.summary ? '<p class="summary">' + esc(p.summary) + "</p>" : "")
      + (tags ? '<div class="tags">' + tags + "</div>" : "")
      + '<div class="meta">'
        + (showDate ? '<span class="card-date">' + esc(fmtShort(p.added)) + "</span>" : "")
        + '<span class="authors">' + authorsLine(p.authors) + "</span>"
      + "</div>"
      + (p.abstract ? '<button class="abstract-toggle">Abstract</button>' : "")
      + "</div>";
    var back = '<div class="card-back">'
      + '<span class="back-label">Abstract</span>'
      + '<p class="abstract">' + esc(p.abstract || "") + "</p>"
      + '<button class="abstract-close">← Back</button>'
      + "</div>";
    return '<article class="card"><div class="card-inner">' + front + back + "</div></article>";
  }

  function renderGrid(el, list, showDate) {
    el.innerHTML = list.map(function (p) { return card(p, showDate); }).join("");
    if (window.renderMathInElement) { renderMathInElement(el, KATEX_OPTS); }
  }

  function setTab(view) {
    [].forEach.call(document.querySelectorAll(".tab"), function (b) {
      b.classList.toggle("active", b.dataset.view === view);
    });
  }

  function renderStrip(active) {
    var strip = $("datestrip");
    strip.innerHTML = DATES.map(function (d) {
      return '<button class="date' + (d === active ? " active" : "")
        + '" data-date="' + d + '">' + esc(fmtShort(d)) + "</button>";
    }).join("");
    var act = strip.querySelector(".date.active");
    if (act) act.scrollIntoView({ inline: "center", block: "nearest" });
  }

  function showDaily(date) {
    if (!byDate[date]) date = latest;
    $("search-view").hidden = true;
    $("daily-view").hidden = false;
    setTab("daily");
    renderStrip(date);
    var list = byDate[date] || [];
    $("day-title").textContent = date ? fmtFull(date) : "No papers yet";
    $("day-count").textContent = plural(list.length);
    renderGrid($("daily-grid"), list, false);
    $("daily-empty").hidden = list.length !== 0;
  }

  function renderPills() {
    var box = $("search-pills");
    var none = Object.keys(searchTags).length === 0;
    var html = '<button class="pill' + (none ? " active" : "") + '" data-tag="">All</button>';
    Object.keys(TAGS).forEach(function (slug) {
      var t = TAGS[slug];
      html += '<button class="pill' + (searchTags[slug] ? " active" : "")
        + '" data-tag="' + slug + '" style="--c:' + t.color + '">' + esc(t.name) + "</button>";
    });
    box.innerHTML = html;
  }

  function runSearch() {
    var q = ($("search-input").value || "").trim().toLowerCase();
    var sel = Object.keys(searchTags);
    var list = PAPERS.filter(function (p) {
      var okTag = !sel.length || (p.tags || []).some(function (t) { return searchTags[t]; });
      if (!okTag) return false;
      if (!q) return true;
      var hay = (p.title + " " + (p.authors || []).join(" ")).toLowerCase();
      return hay.indexOf(q) !== -1;
    });
    $("search-count").textContent = plural(list.length);
    renderGrid($("search-grid"), list, true);
    $("search-empty").hidden = list.length !== 0;
  }

  function showSearch() {
    $("daily-view").hidden = true;
    $("search-view").hidden = false;
    setTab("search");
    renderPills();
    runSearch();
  }

  function route() {
    var h = (location.hash || "").replace(/^#/, "");
    if (h === "search") { showSearch(); return; }
    if (/^\d{4}-\d{2}-\d{2}$/.test(h) && byDate[h]) { showDaily(h); return; }
    showDaily(latest);
  }

  function wire() {
    document.addEventListener("click", function (e) {
      var tab = e.target.closest(".tab");
      if (tab) {
        location.hash = tab.dataset.view === "search" ? "search" : (latest || "");
        return;
      }
      var date = e.target.closest(".date");
      if (date) { location.hash = date.dataset.date; return; }

      var pill = e.target.closest(".pill");
      if (pill) {
        var slug = pill.dataset.tag;
        if (!slug) searchTags = {};
        else if (searchTags[slug]) delete searchTags[slug];
        else searchTags[slug] = true;
        renderPills();
        runSearch();
        return;
      }
      var tog = e.target.closest(".abstract-toggle");
      if (tog) { tog.closest(".card").classList.add("flipped"); return; }
      var cls = e.target.closest(".abstract-close");
      if (cls) { cls.closest(".card").classList.remove("flipped"); return; }
    });
    $("search-input").addEventListener("input", runSearch);
    window.addEventListener("hashchange", route);
  }

  function init(data) {
    TAGS = data.tags || {};
    PAPERS = data.papers || [];
    byDate = {};
    PAPERS.forEach(function (p) {
      (byDate[p.added] = byDate[p.added] || []).push(p);
    });
    DATES = Object.keys(byDate).sort();          // ascending → latest at the right
    latest = DATES.length ? DATES[DATES.length - 1] : null;
    wire();
    route();
  }

  fetch("data.json")
    .then(function (r) { return r.json(); })
    .then(init)
    .catch(function (e) {
      document.querySelector("main").innerHTML =
        '<p class="empty">Could not load papers. ' + esc(String(e)) + "</p>";
    });
})();
