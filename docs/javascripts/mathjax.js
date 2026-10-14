window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"], ["$", "$"]],
    displayMath: [["\\[", "\\]"], ["$$", "$$"]],
    macros: {
      PBIAS: "\\text{PBIAS}",
      NSE: "\\text{NSE}",
      RMSE: "\\text{RMSE}",
      MAE: "\\text{MAE}",
      ρ: "\\rho",
      σ: "\\sigma"
    }
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex"
  },
  jax: ["output/chtml"],
  jsMath2jax: {
    delimiters: [
      {left: "$$", right: "$$", delimiters: "double"},
      {left: "$", right: "$", delimiters: "inline"}
    ]
  }
};

window.addEventListener('load', () => {
  MathJax.typesetPromise().catch(err => console.error('MathJax typesetting failed:', err));
});
