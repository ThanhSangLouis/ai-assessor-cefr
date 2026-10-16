// The product page's 3D (D031): the hero scene turns toward the pointer and
// cards marked data-tilt lean toward it, with a glare where it points.
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

  // The scene eases toward where the pointer is instead of jumping there:
  // each frame covers a share of the remaining distance, and the loop stops
  // once there is nothing left to cover.
  const hero = document.querySelector(".lp-hero");
  const scene = document.querySelector("[data-scene]");
  if (hero && scene) {
    const EASE = 0.08;
    let target = { x: 0, y: 0 };
    let now = { x: 0, y: 0 };
    let frame = 0;

    const step = () => {
      now.x += (target.x - now.x) * EASE;
      now.y += (target.y - now.y) * EASE;
      scene.style.setProperty("--px", now.x.toFixed(4));
      scene.style.setProperty("--py", now.y.toFixed(4));
      // D037: the terraces under the scene drift the other way, a little.
      hero.style.setProperty("--px", now.x.toFixed(4));
      hero.style.setProperty("--py", now.y.toFixed(4));
      const left = Math.abs(target.x - now.x) + Math.abs(target.y - now.y);
      frame = left > 0.0005 ? window.requestAnimationFrame(step) : 0;
    };
    const aim = (x, y) => {
      target = { x, y };
      if (!frame) frame = window.requestAnimationFrame(step);
    };

    hero.addEventListener("pointermove", (event) => {
      const box = hero.getBoundingClientRect();
      aim(
        ((event.clientX - box.left) / box.width) * 2 - 1,
        ((event.clientY - box.top) / box.height) * 2 - 1
      );
    });
    hero.addEventListener("pointerleave", () => aim(0, 0));
  }

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
