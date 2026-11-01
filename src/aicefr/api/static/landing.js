// The product page's 3D (D031): cards marked data-tilt lean toward the pointer,
// with a glare where it points. (D078 removed the hero scene.)
//
// Decoration only. With reduced motion asked for, or on a touch screen where
// there is no pointer to follow, this does nothing and the page keeps its
// resting angles from style.css. It writes CSS custom properties and nothing
// else; every transform is in the stylesheet.
(() => {
  "use strict";

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
  if (reduced.matches || !finePointer.matches) return;

  // A tilting card: the edge nearest the pointer comes forward, at most MAX
  // degrees -- enough to feel, not enough to look like a toy. Leaving the
  // card hands it back to the stylesheet, which eases it to its resting angle
  // (a mock-up rests tilted, a step card rests flat).
  const MAX = 5;
  for (const card of document.querySelectorAll("[data-tilt]")) {
    card.addEventListener("pointermove", (event) => {
      const box = card.getBoundingClientRect();
      const x = (event.clientX - box.left) / box.width;
      const y = (event.clientY - box.top) / box.height;
      card.classList.add("is-tilting");
      card.style.setProperty("--tilt-x", ((y - 0.5) * 2 * MAX).toFixed(2) + "deg");
      card.style.setProperty("--tilt-y", ((0.5 - x) * 2 * MAX).toFixed(2) + "deg");
      card.style.setProperty("--glare-x", (x * 100).toFixed(1) + "%");
      card.style.setProperty("--glare-y", (y * 100).toFixed(1) + "%");
    });
    card.addEventListener("pointerleave", () => {
      card.classList.remove("is-tilting");
      for (const name of ["--tilt-x", "--tilt-y", "--glare-x", "--glare-y"]) {
        card.style.removeProperty(name);
      }
    });
  }
})();
