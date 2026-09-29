/* Mermaid.js loader for the HydroCast MkDocs site.
   Renders every ```mermaid fenced block written in docs_src/*.md.
   Re-runs on instant-navigation page swaps (Material's document$ event). */

(function () {
  const MERMAID_SRC =
    "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js";

  let loading = null;

  function loadMermaid() {
    if (window.mermaid) return Promise.resolve(window.mermaid);
    if (loading) return loading;

    loading = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = MERMAID_SRC;
      script.integrity =
        "sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz";
      script.crossOrigin = "anonymous";
      script.onload = () => {
        window.mermaid.initialize({
          startOnLoad: false,
          securityLevel: "loose",
          theme: document.body.getAttribute("data-md-color-scheme") === "slate"
            ? "dark"
            : "default",
          fontFamily: "Roboto, Helvetica, Arial, sans-serif",
          flowchart: { htmlLabels: true, curve: "basis", useMaxWidth: true },
          sequence: { useMaxWidth: true },
          gantt: { useMaxWidth: true },
        });
        resolve(window.mermaid);
      };
      script.onerror = () =>
        reject(new Error("Failed to load mermaid from CDN"));
      document.head.appendChild(script);
    });
    return loading;
  }

  async function renderDiagrams() {
    const nodes = document.querySelectorAll(".mermaid:not([data-processed])");
    if (!nodes.length) return;

    try {
      const mermaid = await loadMermaid();
      for (const node of nodes) {
        if (node.getAttribute("data-processed") === "true") continue;
        // Superfences emits the raw source as the element's text content.
        const id = "mmd-" + Math.random().toString(36).slice(2);
        try {
          const { svg } = await mermaid.render(id, node.textContent);
          node.innerHTML = svg;
          node.setAttribute("data-processed", "true");
        } catch (err) {
          // Surface the syntax error inline instead of leaving a blank box.
          node.innerHTML =
            '<pre class="hydrocast-figure"><code>Diagram render error: ' +
            String(err) +
            "</code></pre>";
          node.setAttribute("data-processed", "error");
        }
      }
    } catch (err) {
      document.querySelectorAll(".mermaid:not([data-processed])").forEach((n) => {
        n.innerHTML =
          '<p class="md-typeset"><em>Mermaid diagrams require network access ' +
          "to the jsDelivr CDN. The ASCII figures on this page carry the same " +
          "information.</em></p>";
        n.setAttribute("data-processed", "offline");
      });
    }
  }

  // Material dispatches document$ on every instant-navigation page swap.
  if (typeof document$ !== "undefined") {
    document$.subscribe(() => setTimeout(renderDiagrams, 0));
  } else {
    document.addEventListener("DOMContentLoaded", renderDiagrams);
  }

  // Re-theme Mermaid when the light/dark toggle is used.
  document.addEventListener("click", (e) => {
    if (!e.target.closest("[data-md-color-media]")) return;
    if (window.mermaid) {
      window.mermaid.initialize({ theme: "default" });
    }
  });
})();
