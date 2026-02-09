(() => {
  const TOUR_KEY = "goalixa_onboarding_v1";

  const isStorageAvailable = () => {
    try {
      const probe = "__gx_tour__";
      localStorage.setItem(probe, "1");
      localStorage.removeItem(probe);
      return true;
    } catch (error) {
      return false;
    }
  };

  const isTourDone = () => {
    if (!isStorageAvailable()) {
      return false;
    }
    return localStorage.getItem(TOUR_KEY) === "done";
  };

  const markTourDone = () => {
    if (!isStorageAvailable()) {
      return;
    }
    localStorage.setItem(TOUR_KEY, "done");
  };

  const isForced = () => {
    const params = new URLSearchParams(window.location.search);
    const value = params.get("tour");
    return value === "1" || value === "true";
  };

  const isElementVisible = (el) => {
    if (!el) {
      return false;
    }
    if (el.hasAttribute("hidden")) {
      return false;
    }
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") {
      return false;
    }
    return el.getClientRects().length > 0;
  };

  const collectSteps = () => {
    const page = document.body?.dataset.page || "";
    return Array.from(document.querySelectorAll("[data-tour-step]"))
      .map((element) => {
        const order = Number.parseInt(element.dataset.tourStep || "", 10);
        if (Number.isNaN(order)) {
          return null;
        }
        const targetPage = element.dataset.tourPage || "";
        if (targetPage && targetPage !== page) {
          return null;
        }
        if (!isElementVisible(element)) {
          return null;
        }
        return {
          element,
          order,
          title: element.dataset.tourTitle || "",
          text: element.dataset.tourText || "",
          position: element.dataset.tourPosition || "bottom",
        };
      })
      .filter(Boolean)
      .sort((a, b) => a.order - b.order);
  };

  const initTour = () => {
    if (!isForced() && isTourDone()) {
      return;
    }

    const steps = collectSteps();
    if (!steps.length) {
      return;
    }

    let currentIndex = 0;
    let activeElement = null;
    let isOpen = true;

    const overlay = document.createElement("div");
    overlay.className = "tour-overlay";
    overlay.innerHTML = `
      <div class="tour-backdrop" data-tour-skip></div>
      <div class="tour-card" role="dialog" aria-modal="true" aria-live="polite">
        <div class="tour-progress"></div>
        <h3 class="tour-title"></h3>
        <p class="tour-text"></p>
        <div class="tour-actions">
          <button class="btn btn-outline-secondary btn-sm" type="button" data-tour-skip>Skip</button>
          <button class="btn btn-primary btn-sm" type="button" data-tour-next>Next</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    document.body.classList.add("tour-active");

    const card = overlay.querySelector(".tour-card");
    const titleEl = overlay.querySelector(".tour-title");
    const textEl = overlay.querySelector(".tour-text");
    const progressEl = overlay.querySelector(".tour-progress");
    const nextButton = overlay.querySelector("[data-tour-next]");
    const skipButtons = overlay.querySelectorAll("[data-tour-skip]");

    const clearActiveTarget = () => {
      if (activeElement) {
        activeElement.classList.remove("tour-target");
      }
    };

    const finishTour = (markDone = true) => {
      if (!isOpen) {
        return;
      }
      isOpen = false;
      clearActiveTarget();
      overlay.remove();
      document.body.classList.remove("tour-active");
      window.removeEventListener("resize", handlePosition);
      window.removeEventListener("scroll", handlePosition, true);
      document.removeEventListener("keydown", handleKeydown);
      if (markDone) {
        markTourDone();
      }
    };

    const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

    const positionCard = () => {
      const step = steps[currentIndex];
      if (!step || !card) {
        return;
      }
      const rect = step.element.getBoundingClientRect();
      const spacing = 14;

      card.style.visibility = "hidden";
      card.style.top = "0px";
      card.style.left = "0px";

      const cardRect = card.getBoundingClientRect();
      const cardWidth = cardRect.width || 320;
      const cardHeight = cardRect.height || 180;

      let top = rect.bottom + spacing;
      let left = rect.left;

      const prefer = step.position;
      if (prefer === "top") {
        top = rect.top - cardHeight - spacing;
        left = rect.left;
      } else if (prefer === "left") {
        top = rect.top;
        left = rect.left - cardWidth - spacing;
      } else if (prefer === "right") {
        top = rect.top;
        left = rect.right + spacing;
      } else if (prefer === "bottom") {
        top = rect.bottom + spacing;
        left = rect.left;
      }

      if (top + cardHeight > window.innerHeight - spacing) {
        const alternateTop = rect.top - cardHeight - spacing;
        if (alternateTop >= spacing) {
          top = alternateTop;
        }
      }

      if (left + cardWidth > window.innerWidth - spacing) {
        left = window.innerWidth - cardWidth - spacing;
      }

      if (left < spacing) {
        left = spacing;
      }

      if (top < spacing) {
        top = spacing;
      }

      top = clamp(top, spacing, window.innerHeight - cardHeight - spacing);
      left = clamp(left, spacing, window.innerWidth - cardWidth - spacing);

      card.style.top = `${top}px`;
      card.style.left = `${left}px`;
      card.style.visibility = "visible";
    };

    const showStep = (index) => {
      const step = steps[index];
      if (!step) {
        finishTour(true);
        return;
      }

      clearActiveTarget();
      activeElement = step.element;
      activeElement.classList.add("tour-target");

      if (titleEl) {
        titleEl.textContent = step.title || "Step";
      }
      if (textEl) {
        textEl.textContent = step.text || "";
      }
      if (progressEl) {
        progressEl.textContent = `Step ${index + 1} of ${steps.length}`;
      }
      if (nextButton) {
        nextButton.textContent = index === steps.length - 1 ? "Done" : "Next";
      }

      step.element.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
      window.setTimeout(positionCard, 160);
    };

    const handleNext = () => {
      if (currentIndex >= steps.length - 1) {
        finishTour(true);
        return;
      }
      currentIndex += 1;
      showStep(currentIndex);
    };

    const handlePosition = () => {
      if (!isOpen) {
        return;
      }
      positionCard();
    };

    const handleKeydown = (event) => {
      if (event.key === "Escape") {
        finishTour(true);
        return;
      }
      if (event.key === "Enter") {
        handleNext();
      }
    };

    skipButtons.forEach((button) => {
      button.addEventListener("click", () => finishTour(true));
    });

    if (nextButton) {
      nextButton.addEventListener("click", handleNext);
    }

    window.addEventListener("resize", handlePosition);
    window.addEventListener("scroll", handlePosition, true);
    document.addEventListener("keydown", handleKeydown);

    showStep(currentIndex);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initTour);
  } else {
    initTour();
  }
})();
