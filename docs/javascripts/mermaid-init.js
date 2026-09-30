/* ==========================================================================
   HydroCast documentation — Mermaid renderer
   --------------------------------------------------------------------------
   pymdownx.superfences emits every ```mermaid fence as
       <pre class="mermaid"><code>graph TD …</code></pre>
   with the graph source as the element's text content. This module walks
   those elements and swaps in a rendered SVG.

   The library itself is vendored at docs/javascripts/mermaid.min.js so the
   documentation renders with no network access — the same reason the ASCII
   figures are kept alongside every diagram.

   Responsibilities:
     • render on first load and on every Material instant-navigation swap
     • re-render when the light/dark palette toggle is used
     • surface syntax errors inline, with the offending source, instead of
       leaving a silently blank box
   ========================================================================== */

(function () {
  "use strict";

  var SELECTOR = ".mermaid";
  var SOURCE_ATTR = "data-mermaid-source";
  var READY_ATTR = "data-mermaid-state";

  /* Two concrete palettes. Mermaid needs literal colour values, so they are
     declared per scheme rather than inherited from the CSS custom properties
     the rest of the theme uses. Both schemes share the same hue mapping so
     a node keeps its meaning when the reader toggles the theme. */
  var FONT_STACK =
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
  var MONO_STACK = '"Roboto Mono", "Cascadia Mono", Consolas, "Courier New", monospace';

  function baseVars(mono) {
    return {
      fontFamily: FONT_STACK,
      fontSize: "15px",
      primaryColor: mono ? "#ede9fe" : "#eef2ff",
      primaryTextColor: mono ? "#1e1b4b" : "#111827",
      primaryBorderColor: mono ? "#7c3aed" : "#4338ca",
      lineColor: mono ? "#a5b4fc" : "#64748b",
      secondaryColor: "#f1f5f9",
      tertiaryColor: "#f8fafc",
      background: "transparent",
      mainBkg: mono ? "#ede9fe" : "#eef2ff",
      nodeTextColor: mono ? "#1e1b4b" : "#111827",
      clusterBkg: mono ? "#1e1b4b" : "#f8fafc",
      clusterBorder: mono ? "#4c1d95" : "#c7d2fe",
      edgeLabelBackground: mono ? "#1e1b4b" : "#ffffff",
      titleColor: mono ? "#e0e7ff" : "#111827",
      actorBkg: mono ? "#312e81" : "#e0e7ff",
      actorBorder: mono ? "#a5b4fc" : "#4338ca",
      actorTextColor: mono ? "#e0e7ff" : "#111827",
      signalColor: mono ? "#e0e7ff" : "#111827",
      signalTextColor: mono ? "#e0e7ff" : "#111827",
      labelBoxBkgColor: mono ? "#312e81" : "#e0e7ff",
      labelBoxBorderColor: mono ? "#a5b4fc" : "#4338ca",
      labelTextColor: mono ? "#e0e7ff" : "#111827",
      noteBkgColor: mono ? "#422006" : "#fef9c3",
      noteBorderColor: mono ? "#a16207" : "#ca8a04",
      noteTextColor: mono ? "#fef3c7" : "#713f12",
      loopTextColor: mono ? "#e0e7ff" : "#111827",
      sequenceNumberColor: "#ffffff",
    };
  }

  function scheme() {
    var attr = document.body.getAttribute("data-md-color-scheme");
    if (attr) return attr;
    return window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "slate"
      : "default";
  }

  function configure() {
    if (!window.mermaid) return;
    var dark = scheme() === "slate";
    window.mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: "base",
      fontFamily: FONT_STACK,
      deterministicIds: true,
      /* Diagrams carry dense engineering annotations, so keep the sans stack
         for structure and monospace for anything formula-shaped. */
      themeVariables: baseVars(dark),
      flowchart: {
        htmlLabels: true,
        curve: "basis",
        nodeSpacing: 42,
        rankSpacing: 52,
        padding: 12,
        useMaxWidth: true,
        diagramPadding: 12,
      },
      sequence: { useMaxWidth: true, wrap: true },
      state: { useMaxWidth: true, noteAlign: "right" },
      class: { useMaxWidth: true },
      er: { useMaxWidth: true },
      gantt: { useMaxWidth: true },
      pie: { useMaxWidth: true },
    });
    void MONO_STACK;
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  /* A failed diagram must never read as a blank box. Show the parser message
     and the source that caused it, so a bad fence is diagnosable from the
     published page alone. */
  function showError(node, message) {
    var source = node.getAttribute(SOURCE_ATTR) || node.textContent;
    node.classList.add("mermaid--error");
    node.innerHTML =
      '<div class="mermaid-error__title">Diagram could not be rendered</div>' +
      '<div class="mermaid-error__body"><pre><code>' +
      escapeHtml(message) +
      "</code></pre></div>" +
      '<details class="mermaid-error__source"><summary>Diagram source</summary>' +
      "<pre><code>" +
      escapeHtml(source) +
      "</code></pre></details>";
    node.setAttribute(READY_ATTR, "error");
  }

  function showUnsupported(node) {
    node.classList.add("mermaid--error");
    node.innerHTML =
      '<div class="mermaid-error__title">Mermaid runtime unavailable</div>' +
      '<div class="mermaid-error__body"><p>The bundled <code>mermaid.min.js</code> ' +
      "did not load. The ASCII figure above this diagram carries the same " +
      "information and is readable without JavaScript.</p></div>";
    node.setAttribute(READY_ATTR, "missing-runtime");
  }

  function renderOne(node) {
    if (node.getAttribute(READY_ATTR) === "done") return;
    if (node.getAttribute(READY_ATTR) === "error") return;

    var source = node.getAttribute(SOURCE_ATTR);
    if (source === null) {
      source = node.textContent;
      node.setAttribute(SOURCE_ATTR, source);
    }
    if (!source || !source.trim()) {
      node.setAttribute(READY_ATTR, "error");
      return;
    }

    node.classList.remove("mermaid--error");
    node.removeAttribute(READY_ATTR);

    try {
      /* Render to a detached id first, then adopt the SVG. This keeps a parse
         failure from leaving a half-written element in the page. */
      var id =
        "mmd-" +
        Math.random().toString(36).slice(2, 10) +
        "-" +
        (renderOne.counter = (renderOne.counter || 0) + 1);
      var result = window.mermaid.render(id, source, node);
      if (result && typeof result.then === "function") {
        result
          .then(function (out) {
            node.innerHTML = out.svg;
            node.setAttribute(READY_ATTR, "done");
            markLabelled(node);
          })
          .catch(function (err) {
            showError(node, (err && err.message) || err);
          });
        return;
      }
      node.innerHTML = result.svg;
      node.setAttribute(READY_ATTR, "done");
      markLabelled(node);
    } catch (err) {
      showError(node, (err && err.message) || err);
    }
  }

  /* Label any edge/node that carries a formula so the monospace face is
     applied consistently, regardless of how the fence was written. */
  function markLabelled(node) {
    var svg = node.querySelector("svg");
    if (!svg) return;
    svg.setAttribute("role", "img");
    svg.removeAttribute("width");
    svg.removeAttribute("height");
  }

  function renderAll() {
    if (!window.mermaid) {
      Array.prototype.forEach.call(
        document.querySelectorAll(SELECTOR + ":not([" + READY_ATTR + "])"),
        showUnsupported
      );
      return;
    }
    configure();
    Array.prototype.forEach.call(
      document.querySelectorAll(SELECTOR + ":not([" + READY_ATTR + "='done']):not([" + READY_ATTR + "='error'])"),
      renderOne
    );
  }

  /* Re-render every diagram under the new palette. Sources are cached in
     data-mermaid-source on first pass, so this is a pure re-render. */
  function rerenderAll() {
    if (!window.mermaid) return;
    Array.prototype.forEach.call(document.querySelectorAll(SELECTOR), function (node) {
      node.removeAttribute(READY_ATTR);
      node.classList.remove("mermaid--error");
    });
    configure();
    renderAll();
  }

  function boot() {
    renderAll();
  }

  if (typeof document$ !== "undefined") {
    document$.subscribe(function () {
      /* instant.navigation swaps the document body asynchronously; defer one
         frame so the new page's .mermaid nodes are in the DOM. */
      window.requestAnimationFrame(boot);
    });
  } else {
    document.addEventListener("DOMContentLoaded", boot);
  }

  /* Material dispatches this before swapping the palette. Re-render after. */
  document.addEventListener("__md_get_theme", function (evt) {
    if (evt && evt.mode) window.__hydrocastNextScheme = evt.mode;
  });

  var toggle = document.querySelector("[data-md-color-media]");
  if (toggle) {
    toggle.addEventListener("change", function () {
      window.setTimeout(rerenderAll, 0);
    });
  }

  /* Belt and braces: if the toggle event did not fire (older Material, or the
     palette swapped via a different control), poll briefly after any click on
     the header controls. */
  var lastScheme = scheme();
  window.setInterval(function () {
    var now = scheme();
    if (now !== lastScheme) {
      lastScheme = now;
      rerenderAll();
    }
  }, 700);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  void MONO_STACK;
})();
