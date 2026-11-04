// The product page's 3D (D031): cards marked data-tilt lean toward the pointer,
// with a glare where it points. The hero scene came back with D092.
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

  // D031: The hero 3D scene holds its resting perspective angle for optimal
  // stability, crystal-clear readability, and 60fps performance without frame drops.

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

// ---------------------------------------------------------------- Hero 3D Stage Interactive Sync
(() => {
  "use strict";

  // Hovering pillars or scale items synchronizes assessment display seamlessly
  const heroPillars = document.querySelector(".lp-pillars");
  const heroScale = document.getElementById("lp-hero-scale");
  const heroBandVal = document.getElementById("lp-hero-band-val");
  const heroBandDesc = document.getElementById("lp-hero-band-desc");
  const heroRangeFill = document.getElementById("lp-hero-range-fill");
  const heroScaleItems = document.querySelectorAll("#lp-hero-scale .scale-item");
  const heroCubes = document.querySelectorAll(".lp-pillars .cube");

  if (heroBandVal && heroRangeFill && heroScaleItems.length && heroCubes.length) {
    const defaultVal = "B1+";
    const defaultDesc = "Độc lập · Chuẩn đầu ra";
    const defaultLeft = "33%";
    const defaultWidth = "22%";

    const resetToDefault = () => {
      heroBandVal.textContent = defaultVal;
      if (heroBandDesc) heroBandDesc.textContent = defaultDesc;
      heroRangeFill.style.left = defaultLeft;
      heroRangeFill.style.width = defaultWidth;
      for (const item of heroScaleItems) {
        item.classList.toggle("is-active", item.getAttribute("data-level") === "B1");
      }
      for (const cube of heroCubes) {
        cube.classList.remove("is-synced");
      }
    };

    const activateLevel = (level, val, desc, left, width, syncCube = false) => {
      heroBandVal.textContent = val;
      if (heroBandDesc && desc) heroBandDesc.textContent = desc;
      heroRangeFill.style.left = left;
      heroRangeFill.style.width = width;
      for (const item of heroScaleItems) {
        item.classList.toggle("is-active", item.getAttribute("data-level") === level);
      }
      for (const cube of heroCubes) {
        cube.classList.toggle("is-synced", syncCube && cube.getAttribute("data-level") === level);
      }
    };

    // 1. Direct pillar hover: updates assessment band display and illuminates pillar
    for (const cube of heroCubes) {
      cube.addEventListener("pointerenter", () => {
        const level = cube.getAttribute("data-level");
        const matchItem = document.querySelector(`#lp-hero-scale .scale-item[data-level="${level}"]`);
        if (matchItem) {
          activateLevel(
            level,
            matchItem.getAttribute("data-val") || level,
            matchItem.getAttribute("data-desc") || "",
            matchItem.getAttribute("data-left") || "33%",
            matchItem.getAttribute("data-width") || "20%",
            true
          );
        }
      });
    }

    if (heroPillars) {
      heroPillars.addEventListener("pointerleave", resetToDefault);
    }
    const heroStage = document.querySelector(".lp-stage");
    if (heroStage) {
      heroStage.addEventListener("pointerleave", resetToDefault);
    }

    // 2. Scale items hover: highlights scale item, updates band score, and lifts corresponding pillar
    for (const item of heroScaleItems) {
      item.addEventListener("pointerenter", () => {
        const level = item.getAttribute("data-level");
        activateLevel(
          level,
          item.getAttribute("data-val") || level,
          item.getAttribute("data-desc") || "",
          item.getAttribute("data-left") || "33%",
          item.getAttribute("data-width") || "20%",
          true
        );
      });
    }

    if (heroScale) {
      heroScale.addEventListener("pointerleave", resetToDefault);
    }
  }
})();

// ---------------------------------------------------------------- Header Nav Active Tracking & Scrollspy
(() => {
  "use strict";

  const nav = document.querySelector(".site-header .site-nav");
  if (!nav) return;

  const links = Array.from(nav.querySelectorAll("a"));
  if (!links.length) return;

  const linkIntro = links.find((a) => {
    const h = a.getAttribute("href") || "";
    return h === "/" || h === "" || a.textContent.includes("Giới thiệu");
  });
  const linkHow = links.find((a) => (a.getAttribute("href") || "").includes("how-it-works"));
  const linkTeachers = links.find((a) => (a.getAttribute("href") || "").includes("for-teachers"));

  const setActiveNav = (name) => {
    for (const a of links) {
      if ((a.getAttribute("href") || "") === "/bands") continue;
      a.removeAttribute("aria-current");
    }
    if (name === "intro" && linkIntro) {
      linkIntro.setAttribute("aria-current", "page");
    } else if (name === "how-it-works" && linkHow) {
      linkHow.setAttribute("aria-current", "page");
    } else if (name === "for-teachers" && linkTeachers) {
      linkTeachers.setAttribute("aria-current", "page");
    }
  };

  let isClickScrolling = false;
  let clickTimeout = null;

  const scrollToTarget = (targetEl, name) => {
    isClickScrolling = true;
    clearTimeout(clickTimeout);
    setActiveNav(name);

    if (name === "intro") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else if (targetEl) {
      const headerOffset = 76;
      const targetY = targetEl.getBoundingClientRect().top + window.pageYOffset - headerOffset;
      window.scrollTo({ top: Math.max(0, targetY), behavior: "smooth" });
    }

    clickTimeout = setTimeout(() => {
      isClickScrolling = false;
    }, 850);
  };

  if (linkIntro) {
    linkIntro.addEventListener("click", (e) => {
      if (window.location.pathname === "/" || window.location.pathname === "") {
        e.preventDefault();
        history.pushState(null, "", window.location.pathname);
        scrollToTarget(null, "intro");
      }
    });
  }

  if (linkHow) {
    linkHow.addEventListener("click", (e) => {
      if (window.location.pathname === "/" || window.location.pathname === "") {
        e.preventDefault();
        const target = document.getElementById("how-it-works");
        history.pushState(null, "", "#how-it-works");
        scrollToTarget(target, "how-it-works");
      }
    });
  }

  if (linkTeachers) {
    linkTeachers.addEventListener("click", (e) => {
      if (window.location.pathname === "/" || window.location.pathname === "") {
        e.preventDefault();
        const target = document.getElementById("for-teachers");
        history.pushState(null, "", "#for-teachers");
        scrollToTarget(target, "for-teachers");
      }
    });
  }

  // Scrollspy tracking
  const onScroll = () => {
    if (isClickScrolling) return;

    const howSection = document.getElementById("how-it-works");
    const teacherSection = document.getElementById("for-teachers");

    const scrollY = window.pageYOffset || document.documentElement.scrollTop;
    const triggerOffset = 180;

    if (teacherSection && scrollY + triggerOffset >= teacherSection.offsetTop) {
      setActiveNav("for-teachers");
    } else if (howSection && scrollY + triggerOffset >= howSection.offsetTop) {
      setActiveNav("how-it-works");
    } else {
      setActiveNav("intro");
    }
  };

  window.addEventListener("scroll", onScroll, { passive: true });

  // Initial check based on current hash
  if (window.location.hash === "#for-teachers") {
    setActiveNav("for-teachers");
  } else if (window.location.hash === "#how-it-works") {
    setActiveNav("how-it-works");
  } else {
    setActiveNav("intro");
  }
})();
