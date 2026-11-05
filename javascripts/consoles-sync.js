/* ==========================================================================
   HydroCast Interactive Consoles Theme Synchronization & URL Resolver
   Ensures embedded Archify diagram iframes sync dynamically with MkDocs Material.
   ========================================================================== */

(function () {
  function getMaterialTheme() {
    var scheme = document.body.getAttribute("data-md-color-scheme");
    return scheme === "slate" ? "dark" : "light";
  }

  function syncConsoles() {
    var theme = getMaterialTheme();
    var iframes = document.querySelectorAll("iframe.hydrocast-diagram-frame");
    iframes.forEach(function (frame) {
      try {
        var currentSrc = frame.getAttribute("src");
        if (currentSrc && currentSrc.indexOf("diagrams/") !== -1) {
          var url = new URL(currentSrc, window.location.href);
          url.searchParams.set("embed", "1");
          url.searchParams.set("theme", theme);
          if (frame.src !== url.href) {
            frame.src = url.href;
          }
        }
      } catch (err) {}
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", syncConsoles);
  } else {
    syncConsoles();
  }

  // Observe theme changes on body
  var observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
      if (mutation.attributeName === "data-md-color-scheme") {
        syncConsoles();
      }
    });
  });

  observer.observe(document.body, {
    attributes: true,
    attributeFilter: ["data-md-color-scheme"]
  });
})();
