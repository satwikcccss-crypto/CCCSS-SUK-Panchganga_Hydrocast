window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true,
    macros: {
      PBIAS: "\\text{PBIAS}",
      NSE: "\\text{NSE}",
      RMSE: "\\text{RMSE}",
      MAE: "\\text{MAE}"
    }
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex"
  }
};

document$.subscribe(() => {
  if (typeof MathJax !== "undefined" && MathJax.typesetPromise) {
    if (MathJax.startup && MathJax.startup.output) {
      MathJax.startup.output.clearCache();
    }
    if (MathJax.typesetClear) {
      MathJax.typesetClear();
    }
    if (MathJax.texReset) {
      MathJax.texReset();
    }
    MathJax.typesetPromise().catch(err => console.error('MathJax typesetting failed:', err));
  }
});

