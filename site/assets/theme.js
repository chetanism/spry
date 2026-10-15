/* Runs before the page paints, so a saved light or dark choice never flashes. */
try {
  var t = localStorage.getItem("spry-theme");
  if (t === "light" || t === "dark") document.documentElement.dataset.theme = t;
} catch (e) {}
