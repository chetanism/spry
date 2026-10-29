/* spry docs — builds the header, sidebar, table of contents, pager and search around each page's
   <main>. Pages hold only their content; the navigation lives here, once. No dependencies. */
(function () {
  "use strict";

  const REPO = "https://github.com/chetanism/spry";

  // Every page, in reading order. The pager follows this order; tests/test_site.py checks that each
  // path exists and that every page under site/ is listed.
  const NAV = [
    { title: "Getting started", items: [
      ["Introduction", "index.html"],
      ["Why spry", "start/why.html"],
      ["Is spry for you?", "start/fit.html"],
      ["spry, Spec Kit and Kiro", "start/compare.html"],
      ["Installation", "start/install.html"],
      ["Quick start", "start/quick-start.html"],
      ["A worked example", "start/example.html"],
    ] },
    { title: "Guides", items: [
      ["Set up a new project", "guides/new-project.html"],
      ["Adopt an existing codebase", "guides/adopt.html"],
      ["Plan the work", "guides/planning.html"],
      ["Write acceptance criteria", "guides/criteria.html"],
      ["Split a story into slices", "guides/slicing.html"],
      ["Build a slice", "guides/building.html"],
      ["Close and merge a slice", "guides/closing.html"],
      ["Reviews with fresh eyes", "guides/reviews.html"],
      ["Checks for QA", "guides/qa.html"],
      ["Bugs and tasks", "guides/bugs-and-tasks.html"],
      ["Record what you learn", "guides/knowledge.html"],
      ["Work as a team", "guides/team.html"],
      ["Use another agent", "guides/other-agents.html"],
      ["Test beyond the slice", "guides/testing.html"],
      ["Keep spry yours", "guides/maintaining.html"],
    ] },
    { title: "Design", items: [
      ["Principles", "design/principles.html"],
      ["The plan is a folder tree", "design/plan-tree.html"],
      ["Status is derived", "design/status.html"],
      ["Where a person decides", "design/decisions.html"],
      ["Written for its reader", "design/audience.html"],
      ["The conflict check", "design/conflicts.html"],
      ["Falsify", "design/falsify.html"],
      ["The gate and test speed", "design/gate.html"],
      ["Agent hooks", "design/hooks.html"],
      ["Generated pages", "design/pages.html"],
      ["Knowledge and size", "design/knowledge.html"],
      ["Coming from writ", "design/writ.html"],
    ] },
    { title: "Reference", items: [
      ["Skills", "reference/skills.html"],
      ["Tool commands", "reference/tool.html"],
      ["Configuration", "reference/config.html"],
      ["Glossary", "reference/glossary.html"],
      ["FAQ", "reference/faq.html"],
    ] },
  ];

  const TOP = [
    ["Guides", "guides/new-project.html", "guides/"],
    ["Design", "design/principles.html", "design/"],
    ["Reference", "reference/skills.html", "reference/"],
  ];

  const ICON = {
    logo: '<svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="var(--accent)"/><path d="M9.5 22.5c6.5.5 12-4 13-13-6.5-.5-12 4-13 13Z" fill="var(--accent-ink)"/><path d="M9.5 22.5 17 15" stroke="var(--accent)" stroke-width="1.6" stroke-linecap="round"/></svg>',
    search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
    menu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    close: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>',
    sun: '<svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    moon: '<svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/></svg>',
    github: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .5a11.5 11.5 0 0 0-3.6 22.4c.6.1.8-.3.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.4 11.4 0 0 1 6 0C17.7 4 18.7 4.4 18.7 4.4c.6 1.7.2 2.9.1 3.2.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A11.5 11.5 0 0 0 12 .5Z"/></svg>',
  };

  // The site root, worked out from this script's own URL (…/assets/site.js), so the site works at
  // any path: a GitHub Pages project site, a custom domain, or a local server.
  const script = document.currentScript;
  const BASE = new URL("../", script ? script.src : location.href);
  const url = (p) => new URL(p, BASE).href;
  const strip = (h) => h.replace(/[#?].*$/, "").replace(/\/$/, "/index.html");

  const pages = NAV.flatMap((g) => g.items.map(([title, path]) => ({ title, path, group: g.title })));
  const here = strip(location.href);
  const current = pages.find((p) => strip(url(p.path)) === here);

  const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const slug = (s) => s.toLowerCase().replace(/[^\w\s-]/g, "").trim().replace(/[\s_]+/g, "-").replace(/-+/g, "-");

  // ---------- Theme ----------

  function store(key, value) {
    try {
      if (value === undefined) return localStorage.getItem(key);
      localStorage.setItem(key, value);
    } catch (e) { return null; }
  }

  function toggleTheme() {
    const root = document.documentElement;
    const dark = root.dataset.theme
      ? root.dataset.theme === "dark"
      : matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    store("spry-theme", root.dataset.theme);
  }

  // ---------- Chrome ----------

  function header() {
    const el = document.createElement("header");
    el.className = "site-header";
    const top = TOP.map(([t, p, prefix]) => {
      const active = current && current.path.startsWith(prefix) ? " active" : "";
      return `<a class="${active.trim()}" href="${url(p)}">${t}</a>`;
    }).join("");
    el.innerHTML = `
      <button class="icon-btn menu-btn" type="button" aria-label="Open navigation" aria-expanded="false">${ICON.menu}</button>
      <a class="brand" href="${url("index.html")}" aria-label="spry home">${ICON.logo}<span>spry</span></a>
      <nav class="header-nav" aria-label="Sections">${top}</nav>
      <div class="header-right">
        <button class="search-btn" type="button" aria-label="Search the docs">${ICON.search}<span class="label">Search</span><kbd>${/Mac|iPhone|iPad/.test(navigator.platform) ? "⌘" : "Ctrl"} K</kbd></button>
        <button class="icon-btn theme-btn" type="button" aria-label="Switch light or dark">${ICON.sun}${ICON.moon}</button>
        <a class="icon-btn" href="${REPO}" aria-label="spry on GitHub">${ICON.github}</a>
      </div>`;
    return el;
  }

  function sidebar() {
    const el = document.createElement("aside");
    el.className = "sidebar";
    el.id = "sidebar";
    el.setAttribute("aria-label", "Documentation");
    const top = TOP.map(([t, p]) => `<li><a href="${url(p)}">${t}</a></li>`).join("");
    el.innerHTML =
      `<div class="sidebar-links"><ul>${top}<li><a href="${REPO}">GitHub</a></li></ul></div>` +
      NAV.map((g) => `
        <div class="group">
          <p class="group-title">${g.title}</p>
          <ul>${g.items.map(([t, p]) => {
            const active = current && current.path === p;
            return `<li><a href="${url(p)}"${active ? ' class="active" aria-current="page"' : ""}>${t}</a></li>`;
          }).join("")}</ul>
        </div>`).join("");
    return el;
  }

  function toc(article) {
    const heads = [...article.querySelectorAll("h2, h3")].filter((h) => !h.closest(".card, .hero"));
    const el = document.createElement("aside");
    el.className = "toc";
    el.setAttribute("aria-label", "On this page");
    if (heads.length < 2) return el;
    el.innerHTML = `<p class="toc-title">On this page</p><ul>${heads.map((h) =>
      `<li class="l${h.tagName[1]}"><a href="#${h.id}">${esc(h.dataset.title)}</a></li>`).join("")}</ul>`;

    const links = new Map([...el.querySelectorAll("a")].map((a) => [a.getAttribute("href").slice(1), a]));
    const visible = new Set();
    const spy = new IntersectionObserver((entries) => {
      entries.forEach((e) => (e.isIntersecting ? visible.add(e.target.id) : visible.delete(e.target.id)));
      let id = null;
      for (const h of heads) {
        if (visible.has(h.id)) { id = h.id; break; }
        if (h.getBoundingClientRect().top < 120) id = h.id;
      }
      links.forEach((a, key) => a.classList.toggle("active", key === id));
    }, { rootMargin: "-60px 0px -60% 0px" });
    heads.forEach((h) => spy.observe(h));
    return el;
  }

  function enhance(article) {
    // Headings: stable ids and a hover anchor.
    const seen = new Set();
    article.querySelectorAll("h2, h3").forEach((h) => {
      h.dataset.title = h.textContent.trim();
      if (!h.id) {
        let id = slug(h.textContent), n = 2;
        while (seen.has(id)) id = `${slug(h.textContent)}-${n++}`;
        h.id = id;
      }
      seen.add(h.id);
      if (!h.closest(".card")) {
        const a = document.createElement("a");
        a.className = "anchor"; a.href = `#${h.id}`; a.textContent = "#";
        a.setAttribute("aria-label", `Link to ${h.dataset.title}`);
        h.prepend(a);
      }
    });

    // Tables scroll sideways on a phone instead of widening the page.
    article.querySelectorAll("table").forEach((t) => {
      if (t.parentElement.classList.contains("table-wrap")) return;
      const w = document.createElement("div");
      w.className = "table-wrap";
      t.replaceWith(w); w.append(t);
    });

    // Code blocks: a frame, an optional label (data-label) and a copy button.
    article.querySelectorAll("pre").forEach((pre) => {
      if (pre.parentElement.classList.contains("code")) return;
      const w = document.createElement("div");
      w.className = "code";
      pre.replaceWith(w); w.append(pre);
      if (pre.dataset.label) {
        const l = document.createElement("span");
        l.className = "code-label"; l.textContent = pre.dataset.label; w.prepend(l);
      }
      const b = document.createElement("button");
      b.className = "copy"; b.type = "button"; b.textContent = "Copy";
      b.addEventListener("click", () => {
        const text = [...pre.querySelectorAll(".p")].length
          ? [...pre.cloneNode(true).childNodes].map((n) => (n.classList && (n.classList.contains("p") || n.classList.contains("c")) ? "" : n.textContent)).join("")
          : pre.textContent;
        navigator.clipboard.writeText(text.replace(/\n{2,}$/, "\n").trim()).then(() => {
          b.textContent = "Copied"; setTimeout(() => (b.textContent = "Copy"), 1400);
        }, () => { b.textContent = "Press ⌘C"; });
      });
      w.append(b);
    });

    // The group name above the title, like a breadcrumb.
    const h1 = article.querySelector("h1");
    if (current && h1 && !article.querySelector(".eyebrow") && current.path !== "index.html") {
      const p = document.createElement("p");
      p.className = "eyebrow"; p.textContent = current.group;
      h1.before(p);
    }
  }

  function pager(article) {
    if (!current) return;
    const i = pages.indexOf(current);
    const prev = pages[i - 1], next = pages[i + 1];
    const nav = document.createElement("nav");
    nav.className = "pager";
    nav.setAttribute("aria-label", "Previous and next page");
    nav.innerHTML =
      (prev ? `<a class="prev" href="${url(prev.path)}"><small>← Previous</small><span>${prev.title}</span></a>` : "") +
      (next ? `<a class="next" href="${url(next.path)}"><small>Next →</small><span>${next.title}</span></a>` : "");
    article.append(nav);
    const foot = document.createElement("footer");
    foot.className = "page-foot";
    foot.innerHTML = `<a href="${REPO}/edit/main/site/${current.path}">Suggest a change to this page</a><span>spry · MIT licence</span>`;
    article.append(foot);
  }

  // ---------- Search ----------
  // The index is built in the browser the first time search opens: every page in NAV is fetched
  // and split into sections at its h2 / h3. Small site, so no prebuilt index to keep in step.

  let index = null;

  async function buildIndex() {
    const parser = new DOMParser();
    const docs = await Promise.all(pages.map(async (p) => {
      const res = await fetch(url(p.path));
      if (!res.ok) throw new Error(res.status);
      return [p, parser.parseFromString(await res.text(), "text/html")];
    }));
    const out = [];
    for (const [p, doc] of docs) {
      const art = doc.querySelector("main article");
      if (!art) continue;
      art.querySelectorAll("pre").forEach((n) => (n.textContent = " " + n.textContent + " "));
      // Space between cells and blocks, so "removed" and "Nothing" in two cells never read as one word.
      art.querySelectorAll("td, th, li, p, dt, dd, div, span.step, br").forEach((n) => n.append(" "));
      let sec = { page: p, heading: p.title, id: "", text: "" };
      const seen = new Set();
      const walk = (node) => {
        for (const n of node.children) {
          if (/^H[23]$/.test(n.tagName)) {
            out.push(sec);
            let id = n.id || slug(n.textContent), k = 2;
            if (!n.id) while (seen.has(id)) id = `${slug(n.textContent)}-${k++}`;
            seen.add(id);
            sec = { page: p, heading: n.textContent.trim(), id, text: "" };
          } else if (n.tagName === "H1") {
            continue;
          } else if (n.querySelector && n.querySelector("h2, h3") && !n.matches(".card, .cards")) {
            walk(n);
          } else {
            sec.text += " " + n.textContent;
          }
        }
      };
      walk(art);
      out.push(sec);
    }
    out.forEach((s) => {
      s.text = s.text.replace(/\s+/g, " ").trim();
      s.hay = (s.heading + " " + s.text).toLowerCase();
    });
    return out;
  }

  function search(q) {
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) return [];
    const hits = [];
    for (const s of index) {
      if (!terms.every((t) => s.hay.includes(t) || s.page.title.toLowerCase().includes(t))) continue;
      let score = 0;
      const head = s.heading.toLowerCase(), title = s.page.title.toLowerCase();
      for (const t of terms) {
        if (title.includes(t)) score += 6;
        if (head.includes(t)) score += 8;
        if (head.startsWith(t)) score += 3;
        score += Math.min(4, s.text.toLowerCase().split(t).length - 1);
      }
      if (!s.id) score += 2;
      hits.push([score, s]);
    }
    return hits.sort((a, b) => b[0] - a[0]).slice(0, 12).map((h) => h[1]);
  }

  function snippet(text, terms) {
    const low = text.toLowerCase();
    let at = -1;
    for (const t of terms) { at = low.indexOf(t); if (at >= 0) break; }
    const start = Math.max(0, at - 50);
    let s = (start ? "…" : "") + text.slice(start, start + 170) + (text.length > start + 170 ? "…" : "");
    s = esc(s);
    for (const t of terms) {
      if (t.length < 2) continue;
      s = s.replace(new RegExp(`(${t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi"), "<mark>$1</mark>");
    }
    return s;
  }

  function searchDialog() {
    const el = document.createElement("div");
    el.className = "search-dialog";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-modal", "true");
    el.setAttribute("aria-label", "Search the docs");
    el.innerHTML = `
      <div class="search-panel">
        <div class="search-field">${ICON.search}<input type="search" placeholder="Search the docs — try “slice”, “falsify”, “QA”" autocomplete="off" spellcheck="false" aria-label="Search"><button class="icon-btn" type="button" aria-label="Close search">${ICON.close}</button></div>
        <ul class="search-results" role="listbox"></ul>
        <div class="search-foot"><span><kbd>↑</kbd> <kbd>↓</kbd> to move</span><span><kbd>↵</kbd> to open</span><span><kbd>esc</kbd> to close</span></div>
      </div>`;
    const input = el.querySelector("input");
    const list = el.querySelector(".search-results");
    let sel = 0;

    const render = () => {
      const q = input.value.trim();
      if (!q) { list.innerHTML = `<li class="search-empty">Type to search every page.</li>`; return; }
      if (!index) { list.innerHTML = `<li class="search-empty">Loading…</li>`; return; }
      const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
      const hits = search(q);
      sel = 0;
      list.innerHTML = hits.length
        ? hits.map((s, i) => `<li><a href="${url(s.page.path)}${s.id ? "#" + s.id : ""}" class="${i === 0 ? "sel" : ""}">
            <span class="r-path">${esc(s.page.group)} › ${esc(s.page.title)}</span>
            <span class="r-title">${esc(s.heading)}</span>
            ${s.text ? `<span class="r-snip">${snippet(s.text, terms)}</span>` : ""}</a></li>`).join("")
        : `<li class="search-empty">Nothing found for “${esc(q)}”.</li>`;
    };

    const move = (d) => {
      const items = [...list.querySelectorAll("a")];
      if (!items.length) return;
      items[sel].classList.remove("sel");
      sel = (sel + d + items.length) % items.length;
      items[sel].classList.add("sel");
      items[sel].scrollIntoView({ block: "nearest" });
    };

    input.addEventListener("input", render);
    input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { e.preventDefault(); move(1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
      else if (e.key === "Enter") { const a = list.querySelector("a.sel"); if (a) { location.href = a.href; close(); } }
    });
    list.addEventListener("click", (e) => { if (e.target.closest("a")) close(); });
    el.addEventListener("click", (e) => { if (e.target === el) close(); });
    el.querySelector(".search-field .icon-btn").addEventListener("click", close);

    function open() {
      el.classList.add("open");
      input.focus(); input.select();
      render();
      if (!index) {
        buildIndex().then((i) => { index = i; render(); }, () => {
          list.innerHTML = `<li class="search-empty">Search needs the site served over http — try <code>python3 -m http.server -d site</code>.</li>`;
        });
      }
    }
    function close() { el.classList.remove("open"); }
    el.openSearch = open;
    el.closeSearch = close;
    return el;
  }

  // ---------- Assemble ----------

  function init() {
    const main = document.querySelector("main");
    const article = main && main.querySelector("article");
    if (!main || !article) return;
    main.classList.add("doc");
    main.id = main.id || "content";

    const skip = document.createElement("a");
    skip.className = "skip"; skip.href = "#content"; skip.textContent = "Skip to content";

    enhance(article);
    pager(article);

    const layout = document.createElement("div");
    layout.className = "layout";
    main.replaceWith(layout);
    const side = sidebar();
    const scrim = document.createElement("div");
    scrim.className = "scrim";
    layout.append(side, main, toc(article));

    const head = header();
    const dialog = searchDialog();
    document.body.prepend(skip, head);
    document.body.append(scrim, dialog);

    const menu = head.querySelector(".menu-btn");
    const setNav = (open) => {
      document.body.classList.toggle("nav-open", open);
      menu.setAttribute("aria-expanded", String(open));
      menu.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
      menu.innerHTML = open ? ICON.close : ICON.menu;
    };
    menu.addEventListener("click", () => setNav(!document.body.classList.contains("nav-open")));
    scrim.addEventListener("click", () => setNav(false));
    side.addEventListener("click", (e) => { if (e.target.closest("a")) setNav(false); });

    head.querySelector(".theme-btn").addEventListener("click", toggleTheme);
    head.querySelector(".search-btn").addEventListener("click", dialog.openSearch);
    document.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); dialog.openSearch(); }
      else if (e.key === "/" && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) { e.preventDefault(); dialog.openSearch(); }
      else if (e.key === "Escape") { dialog.closeSearch(); setNav(false); }
    });

    // Keep the active sidebar link in view on long lists.
    const active = side.querySelector("a.active");
    if (active && active.offsetTop > side.clientHeight - 80) side.scrollTop = active.offsetTop - side.clientHeight / 3;

    if (location.hash) {
      const t = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (t) requestAnimationFrame(() => t.scrollIntoView());
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
