(() => {
  const storageKey = "theme";
  const sidebarKey = "sidebar";
  const root = document.documentElement;
  const body = document.body;
  const openDropdowns = () => {
    document.querySelectorAll(".timer-dropdown").forEach((dropdown) => {
      dropdown.classList.add("is-open");
    });
  };
  const toggle = () => {
    const current = root.getAttribute("data-theme") || "light";
    const next = current === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    localStorage.setItem(storageKey, next);
  };

  const saved = localStorage.getItem(storageKey);
  if (saved) {
    root.setAttribute("data-theme", saved);
  }

  const setSidebarState = (state) => {
    if (!body) {
      return;
    }
    if (state === "collapsed") {
      body.setAttribute("data-sidebar", "collapsed");
    } else {
      body.removeAttribute("data-sidebar");
    }
    document.querySelectorAll("[data-sidebar-toggle]").forEach((button) => {
      button.setAttribute("aria-pressed", state === "collapsed" ? "true" : "false");
    });
  };

  const savedSidebar = localStorage.getItem(sidebarKey);
  if (savedSidebar) {
    setSidebarState(savedSidebar);
  }

  const pomodoroKey = "pomodoroState";
  const pomodoroDefaults = {
    mode: "work",
    remaining: 25 * 60,
    isRunning: false,
    completedWork: 0,
    lastTick: null,
    taskId: null,
    taskName: null,
    taskRunning: false,
  };
  const pomodoroPresets = {
    work: 25 * 60,
    short: 5 * 60,
    long: 15 * 60,
  };
  const reminderKey = "pomodoroReminderSettings";
  const reminderLastKey = "pomodoroReminderLastAt";
  const reminderDefaults = {
    enabled: false,
    interval_minutes: 30,
    show_system: true,
    show_toast: true,
    title: "Tracking reminder",
    message: "Start a Pomodoro to keep tracking your focus.",
  };

  const loadPomodoro = () => {
    try {
      const raw = localStorage.getItem(pomodoroKey);
      if (!raw) {
        return { ...pomodoroDefaults };
      }
      return { ...pomodoroDefaults, ...JSON.parse(raw) };
    } catch (error) {
      return { ...pomodoroDefaults };
    }
  };

  const savePomodoro = (state) => {
    localStorage.setItem(pomodoroKey, JSON.stringify(state));
  };

  const showPomodoroToast = (title, message) => {
    const container = document.getElementById("toast-stack");
    if (!container) {
      return;
    }
    const toast = document.createElement("div");
    toast.className = "toast-card";
    toast.innerHTML = `
      <div class="toast-title">${title}</div>
      <div class="toast-message">${message}</div>
      <button class="toast-close" type="button" aria-label="Dismiss">×</button>
    `;
    const removeToast = () => {
      toast.classList.add("is-hidden");
      setTimeout(() => toast.remove(), 300);
    };
    toast.querySelector(".toast-close")?.addEventListener("click", removeToast);
    container.appendChild(toast);
    setTimeout(removeToast, 6000);
  };

  window.showPomodoroToast = showPomodoroToast;

  const getNextPomodoroMode = (state) => {
    if (state.mode === "work") {
      const nextWork = state.completedWork + 1;
      return nextWork % 4 === 0 ? "long" : "short";
    }
    return "work";
  };

  const sendSystemNotification = (title, body) => {
    if (!("Notification" in window)) {
      return;
    }
    if (Notification.permission === "granted") {
      new Notification(title, { body });
    }
  };

  const ensureSystemNotificationPermission = () => {
    if (!("Notification" in window)) {
      return;
    }
    if (Notification.permission === "default") {
      Notification.requestPermission().catch(() => {});
    }
  };

  let reminderSettings = { ...reminderDefaults };

  const loadReminderSettings = () => {
    try {
      const raw = localStorage.getItem(reminderKey);
      if (raw) {
        reminderSettings = { ...reminderDefaults, ...JSON.parse(raw) };
      }
    } catch (error) {
      reminderSettings = { ...reminderDefaults };
    }
  };

  const saveReminderSettings = (settings) => {
    reminderSettings = { ...reminderDefaults, ...settings };
    localStorage.setItem(reminderKey, JSON.stringify(reminderSettings));
  };

  const fetchReminderSettings = () => {
    fetch("/api/settings/notifications")
      .then((response) => {
        if (!response.ok) {
          return null;
        }
        return response.json();
      })
      .then((data) => {
        if (data) {
          saveReminderSettings(data);
        }
      })
      .catch(() => {});
  };

  const maybeSendReminder = () => {
    if (!reminderSettings.enabled) {
      return;
    }
    if (reminderSettings.show_system) {
      ensureSystemNotificationPermission();
    }
    const state = loadPomodoro();
    if (state.isRunning) {
      return;
    }
    const intervalMinutes = Math.max(
      1,
      Math.min(parseInt(reminderSettings.interval_minutes || 30, 10), 240),
    );
    const intervalMs = intervalMinutes * 60 * 1000;
    const now = Date.now();
    const last = parseInt(localStorage.getItem(reminderLastKey) || "0", 10);
    if (now - last < intervalMs) {
      return;
    }
    localStorage.setItem(reminderLastKey, String(now));
    if (reminderSettings.show_toast) {
      showPomodoroToast(reminderSettings.title, reminderSettings.message);
    }
    if (reminderSettings.show_system) {
      sendSystemNotification(reminderSettings.title, reminderSettings.message);
    }
  };

  const pomodoroDisplay = document.getElementById("pomodoro-display");
  if (!pomodoroDisplay) {
    loadReminderSettings();
    fetchReminderSettings();
    setInterval(maybeSendReminder, 30000);
    setInterval(() => {
      const state = loadPomodoro();
      if (!state.isRunning || !state.lastTick) {
        return;
      }
      const elapsed = Math.floor((Date.now() - state.lastTick) / 1000);
      if (elapsed < state.remaining) {
        return;
      }
      if (state.mode === "work" && state.taskId) {
        fetch(`/api/tasks/${state.taskId}/stop`, { method: "POST" }).catch(() => {});
        showPomodoroToast("Focus complete", "Time for a break.");
        sendSystemNotification("Focus complete", "Time for a break.");
        state.completedWork += 1;
      } else {
        showPomodoroToast("Break complete", "Time to focus.");
        sendSystemNotification("Break complete", "Time to focus.");
      }
      state.isRunning = false;
      state.lastTick = null;
      state.taskRunning = false;
      state.mode = getNextPomodoroMode(state);
      state.remaining = pomodoroPresets[state.mode] || pomodoroPresets.work;
      savePomodoro(state);
    }, 1000);
  }

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    const button = target.closest("[data-theme-toggle]");
    const sidebarButton = target.closest("[data-sidebar-toggle]");
    if (button) {
      toggle();
    }
    if (sidebarButton) {
      const current = body?.getAttribute("data-sidebar") === "collapsed" ? "collapsed" : "expanded";
      const next = current === "collapsed" ? "expanded" : "collapsed";
      setSidebarState(next);
      localStorage.setItem(sidebarKey, next);
    }
    if (target.closest(".timer-select")) {
      openDropdowns();
    }
    if (target.closest(".timer-list button")) {
      const input = target.closest(".timer-select")?.querySelector("#task-picker");
      if (input) {
        input.value = target.textContent || "";
      }
      document.querySelectorAll(".timer-dropdown").forEach((dropdown) => {
        dropdown.classList.remove("is-open");
      });
    }
    if (target.closest(".timer-dropdown") === null && !target.closest(".timer-select")) {
      document.querySelectorAll(".timer-dropdown").forEach((dropdown) => {
        dropdown.classList.remove("is-open");
      });
    }
  });

  document.addEventListener("submit", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    const form = target.closest("form[data-action][data-task-id]");
    if (!form) {
      return;
    }
    const action = form.dataset.action;
    const taskId = form.dataset.taskId;
    const taskName = form.dataset.taskName || null;
    if (!taskId || !action) {
      return;
    }
    const state = loadPomodoro();
    if (action === "start") {
      state.mode = "work";
      state.remaining = pomodoroPresets.work;
      state.isRunning = true;
      state.lastTick = Date.now();
      state.taskId = taskId;
      state.taskName = taskName;
      state.taskRunning = true;
      savePomodoro(state);
    } else if (action === "stop") {
      if (String(state.taskId) === String(taskId)) {
        state.isRunning = false;
        state.lastTick = null;
        state.taskRunning = false;
        savePomodoro(state);
      }
    }
  });
})();
