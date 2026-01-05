(() => {
  const container = document.getElementById("global-timer");
  if (!container) {
    return;
  }

  const valueEl = container.querySelector("[data-global-timer-value]");
  const metaEl = container.querySelector("[data-global-timer-meta]");
  const taskEl = container.querySelector("[data-global-timer-task]");
  const dismissButton = container.querySelector("[data-global-timer-dismiss]");
  const baseTitle = document.title;

  const storageKey = "pomodoroState";
  const presets = {
    work: 25 * 60,
    short: 5 * 60,
    long: 15 * 60,
  };
  const defaultState = {
    mode: "work",
    remaining: presets.work,
    isRunning: false,
    completedWork: 0,
    lastTick: null,
    taskName: null,
  };

  const formatClock = (seconds) => {
    const safe = Math.max(0, Math.floor(seconds || 0));
    const minutes = Math.floor(safe / 60);
    const remaining = safe % 60;
    return `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
  };

  const modeLabel = (mode) => {
    if (mode === "short") {
      return "Short Break";
    }
    if (mode === "long") {
      return "Long Break";
    }
    return "Focus";
  };

  const loadState = () => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) {
        return { ...defaultState };
      }
      return { ...defaultState, ...JSON.parse(raw) };
    } catch (error) {
      return { ...defaultState };
    }
  };

  const saveState = (state) => {
    localStorage.setItem(storageKey, JSON.stringify(state));
  };

  const applyElapsed = (state, elapsedSeconds) => {
    let remaining = state.remaining;
    let mode = state.mode;
    let completedWork = state.completedWork;
    let secondsLeft = elapsedSeconds;
    let completedAny = false;

    while (secondsLeft > 0) {
      if (remaining > secondsLeft) {
        remaining -= secondsLeft;
        secondsLeft = 0;
      } else {
        secondsLeft -= remaining;
        if (mode === "work") {
          completedWork += 1;
        }
        mode = mode === "work" ? (completedWork % 4 === 0 ? "long" : "short") : "work";
        remaining = presets[mode];
        completedAny = true;
      }
    }

    state.remaining = remaining;
    state.mode = mode;
    state.completedWork = completedWork;
    if (completedAny) {
      if (state.mode === "work") {
        state.isRunning = false;
        state.lastTick = null;
      } else {
        state.isRunning = true;
        state.lastTick = Date.now();
      }
    } else {
      state.lastTick = Date.now();
    }
  };

  const updateTitle = (state) => {
    if (!state.isRunning) {
      document.title = baseTitle;
      return;
    }
    const time = formatClock(state.remaining);
    const mode = modeLabel(state.mode);
    const taskLabel = state.taskName ? ` - ${state.taskName}` : "";
    document.title = `${time} · ${mode}${taskLabel}`;
  };

  const renderState = (state) => {
    if (valueEl) {
      valueEl.textContent = formatClock(state.remaining);
    }
    if (metaEl) {
      const status = state.isRunning ? modeLabel(state.mode) : `Paused · ${modeLabel(state.mode)}`;
      metaEl.textContent = status;
    }
    if (taskEl) {
      taskEl.textContent = state.taskName ? `• ${state.taskName}` : "";
    }
    updateTitle(state);
  };

  const update = () => {
    const state = loadState();
    if (state.isRunning && state.lastTick) {
      const elapsed = Math.floor((Date.now() - state.lastTick) / 1000);
      if (elapsed > 0) {
        applyElapsed(state, elapsed);
        saveState(state);
      }
    }
    renderState(state);
  };

  const scheduleAutoHide = () => {
    window.clearTimeout(window.globalTimerAutoHideId);
    window.globalTimerAutoHideId = window.setTimeout(() => {
      container.classList.add("is-hidden");
    }, 10000);
  };

  update();
  scheduleAutoHide();
  setInterval(update, 1000);
  window.addEventListener("storage", (event) => {
    if (event.key === storageKey) {
      update();
    }
  });

  dismissButton?.addEventListener("click", (event) => {
    event.preventDefault();
    container.classList.add("is-hidden");
  });
})();
