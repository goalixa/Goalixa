(() => {
  const STATE_KEY = "goalixa_onboarding_state_v3";
  const SESSION_KEY = "goalixa_onboarding_session_v1";
  const NAV_KEY = "goalixa_onboarding_nav_v1";
  const RESTART_ON_LOAD = false;

  const steps = [
    {
      id: "labels-create",
      page: "labels",
      selector: '[data-tour-id="labels-create"]',
      title: "Create tags first",
      text: "Start by defining labels so projects and tasks stay organized.",
      position: "bottom",
      url: "/labels",
    },
    {
      id: "projects-create",
      page: "projects",
      selector: '[data-tour-id="projects-create"]',
      title: "Create projects",
      text: "Group related work into projects.",
      position: "bottom",
      url: "/projects",
    },
    {
      id: "tasks-create",
      page: "tasks",
      selector: '[data-tour-id="tasks-create"]',
      title: "Add tasks",
      text: "Choose a project, name the task, and tag it.",
      position: "bottom",
      url: "/tasks",
    },
    {
      id: "tasks-list",
      page: "tasks",
      selector: '[data-tour-id="tasks-list"]',
      title: "To-do list",
      text: "Start/stop timers and mark tasks done today here.",
      position: "top",
      url: "/tasks",
    },
    {
      id: "pomodoro",
      page: "timer",
      selector: '[data-tour-id="pomodoro"]',
      title: "Pomodoro sessions",
      text: "Start focus, take breaks, and track sessions.",
      position: "bottom",
      url: "/timer",
    },
    {
      id: "calendar-board",
      page: "calendar",
      selector: '[data-tour-id="calendar-board"]',
      title: "Calendar view",
      text: "Review weekly checks and streaks.",
      position: "top",
      url: "/calendar",
    },
    {
      id: "overview-summary",
      page: "overview",
      selector: '[data-tour-id="overview-summary"]',
      title: "Overview",
      text: "A high-level snapshot of your progress.",
      position: "bottom",
      url: "/overview",
    },
    {
      id: "habits-checklist",
      page: "habits",
      selector: '[data-tour-id="habits-checklist"]',
      title: "Habits checklist",
      text: "Mark daily routines and build streaks.",
      position: "bottom",
      url: "/habits",
    },
    {
      id: "goals-hub",
      page: "goals",
      selector: '[data-tour-id="goals-hub"]',
      title: "Goals",
      text: "Track weekly and long-term outcomes.",
      position: "bottom",
      url: "/goals",
    },
  ];

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

  const isSessionStorageAvailable = () => {
    try {
      const probe = "__gx_tour_session__";
      sessionStorage.setItem(probe, "1");
      sessionStorage.removeItem(probe);
      return true;
    } catch (error) {
      return false;
    }
  };

  const hasSessionFlag = () => {
    if (!isSessionStorageAvailable()) {
      return false;
    }
    return sessionStorage.getItem(SESSION_KEY) === "active";
  };

  const setSessionFlag = () => {
    if (!isSessionStorageAvailable()) {
      return;
    }
    sessionStorage.setItem(SESSION_KEY, "active");
  };

  const getNavIndex = () => {
    if (!isSessionStorageAvailable()) {
      return null;
    }
    const raw = sessionStorage.getItem(NAV_KEY);
    if (!raw) {
      return null;
    }
    const parsed = Number.parseInt(raw, 10);
    return Number.isNaN(parsed) ? null : parsed;
  };

  const setNavIndex = (index) => {
    if (!isSessionStorageAvailable()) {
      return;
    }
    sessionStorage.setItem(NAV_KEY, String(index));
  };

  const clearNavIndex = () => {
    if (!isSessionStorageAvailable()) {
      return;
    }
    sessionStorage.removeItem(NAV_KEY);
  };

  const loadState = () => {
    if (!isStorageAvailable()) {
      return { index: 0, done: false };
    }
    try {
      const raw = localStorage.getItem(STATE_KEY);
      if (!raw) {
        return { index: 0, done: false };
      }
      const parsed = JSON.parse(raw);
      return {
        index: Number.isInteger(parsed.index) ? parsed.index : 0,
        done: Boolean(parsed.done),
      };
    } catch (error) {
      return { index: 0, done: false };
    }
  };

  const saveState = (state) => {
    if (!isStorageAvailable()) {
      return;
    }
    localStorage.setItem(STATE_KEY, JSON.stringify(state));
  };

  const markDone = () => {
    saveState({ index: steps.length - 1, done: true });
  };

  const isForced = () => {
    const params = new URLSearchParams(window.location.search);
    const value = params.get("tour");
    return value === "1" || value === "true" || value === "start" || value === "reset";
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

  const getPage = () => document.body?.dataset.page || "";

  const shouldNavigateToStep = (step) => {
    if (!step || !step.url) {
      return false;
    }
    const page = getPage();
    if (step.page === "*") {
      return window.location.pathname !== step.url;
    }
    return step.page !== page;
  };

  const resolveStep = (index) => {
    const step = steps[index];
    if (!step) {
      return null;
    }
    const page = getPage();
    if (step.page !== "*" && step.page !== page) {
      return null;
    }
    const element = document.querySelector(step.selector);
    if (!isElementVisible(element)) {
      return null;
    }
    return { step, element, index };
  };

  const resolveFromIndex = (startIndex) => {
    for (let i = startIndex; i < steps.length; i += 1) {
      const resolved = resolveStep(i);
      if (resolved) {
        return resolved;
      }
    }
    return null;
  };

  const initTour = () => {
    const isDemo = document.body?.dataset.demo === "1";
    if (!isDemo) {
      return;
    }
    const forced = isForced();
    const navIndex = getNavIndex();
    if (navIndex !== null) {
      clearNavIndex();
    }
    const stored = loadState();
    if (forced) {
      saveState({ index: 0, done: false });
      setSessionFlag();
    } else if (navIndex !== null) {
      saveState({ index: navIndex, done: false });
      setSessionFlag();
    } else if (RESTART_ON_LOAD) {
      saveState({ index: 0, done: false });
    } else {
      if (stored.done && !forced) {
        return;
      }

      if (!stored.done) {
        if (!hasSessionFlag()) {
          saveState({ index: 0, done: false });
        }
        setSessionFlag();
      }
    }

    const startIndex = forced
      ? 0
      : (navIndex !== null ? navIndex : (RESTART_ON_LOAD ? 0 : (loadState().index || 0)));
    const startStep = steps[startIndex];
    if (shouldNavigateToStep(startStep)) {
      saveState({ index: startIndex, done: false });
      window.location.href = startStep.url;
      return;
    }

    const resolved = resolveFromIndex(startIndex);
    if (!resolved) {
      return;
    }

    let currentIndex = resolved.index;
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

    const finishTour = (storeDone = true) => {
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
      if (storeDone) {
        markDone();
      }
    };

    const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

    const positionCard = () => {
      const resolvedStep = resolveStep(currentIndex);
      if (!resolvedStep || !card) {
        return;
      }
      const { step, element } = resolvedStep;
      const rect = element.getBoundingClientRect();
      const spacing = 14;

      card.style.visibility = "hidden";
      card.style.top = "0px";
      card.style.left = "0px";

      const cardRect = card.getBoundingClientRect();
      const cardWidth = cardRect.width || 320;
      const cardHeight = cardRect.height || 180;

      let top = rect.bottom + spacing;
      let left = rect.left;

      const prefer = step.position || "bottom";
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
      const resolvedStep = resolveStep(index);
      if (!resolvedStep) {
        finishTour(true);
        return;
      }

      currentIndex = resolvedStep.index;
      const { step, element } = resolvedStep;

      clearActiveTarget();
      activeElement = element;
      activeElement.classList.add("tour-target");

      if (titleEl) {
        titleEl.textContent = step.title || "Step";
      }
      if (textEl) {
        textEl.textContent = step.text || "";
      }
      if (progressEl) {
        progressEl.textContent = `Step ${currentIndex + 1} of ${steps.length}`;
      }
      if (nextButton) {
        nextButton.textContent = currentIndex >= steps.length - 1 ? "Done" : "Next";
      }

      saveState({ index: currentIndex, done: false });
      element.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
      window.setTimeout(positionCard, 160);
    };

    const advanceToIndex = (nextIndex) => {
      if (nextIndex >= steps.length) {
        finishTour(true);
        return;
      }
      const nextStep = steps[nextIndex];
      if (shouldNavigateToStep(nextStep)) {
        saveState({ index: nextIndex, done: false });
        setNavIndex(nextIndex);
        window.location.href = nextStep.url;
        return;
      }
      showStep(nextIndex);
    };

    const handleNext = () => {
      if (currentIndex >= steps.length - 1) {
        finishTour(true);
        return;
      }
      advanceToIndex(currentIndex + 1);
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
