function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

function formatSeconds(totalSeconds) {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds || 0));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = safeSeconds % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

let tasksState = new Map();
const availableLabels = Array.isArray(window.availableLabels)
  ? window.availableLabels
  : [];

function setTasksState(tasks) {
  tasksState = new Map(
    tasks.map((task) => [
      String(task.id),
      {
        todaySeconds: Number(task.today_seconds || 0),
        isRunning: Boolean(task.is_running),
      },
    ]),
  );
}

function updateTimeDisplay(taskId, todaySeconds) {
  const timeEl = document.querySelector(`.task-time[data-task-id="${taskId}"]`);
  if (timeEl) {
    timeEl.textContent = formatSeconds(todaySeconds);
  }
}

function toggleEditForm(targetId) {
  const form = document.getElementById(targetId);
  if (!form) {
    return;
  }
  const isOpen = form.classList.contains("is-open");
  document.querySelectorAll(".edit-form.is-open").forEach((openForm) => {
    if (openForm !== form) {
      openForm.classList.remove("is-open");
    }
  });
  form.classList.toggle("is-open", !isOpen);
  if (!isOpen) {
    const input = form.querySelector('input[type="text"]');
    if (input) {
      input.focus();
      input.select();
    }
  }
}

function renderLabelChips(labels, scopeId) {
  if (!labels || !labels.length) {
    return "";
  }
  return `<div class="label-list">
    ${labels
      .map(
        (label) => {
          const safeName = escapeHtml(label.name);
          const safeColor = escapeHtml(label.color);
          const formId = `edit-label-${label.id}-${scopeId}`;
          return `<div class="editable-label">
              <span class="label-chip" style="background-color: ${safeColor}" title="${safeName}">${safeName}</span>
              <button class="edit-toggle icon-button" type="button" aria-label="Edit label" data-edit-target="${formId}">
                <i class="bi bi-pencil"></i>
              </button>
              <form id="${formId}" class="edit-form" method="post" action="/labels/${label.id}/edit">
                <input type="text" name="name" value="${safeName}" required />
                <input type="color" name="color" value="${safeColor}" aria-label="Label color" />
                <button class="btn btn-outline-secondary btn-sm" type="submit">
                  <i class="bi bi-check2"></i>
                  Save
                </button>
              </form>
            </div>`;
        },
      )
      .join("")}
  </div>`;
}

function renderTasks(tasks, doneTodayTasks, completedTasks) {
  const container = document.getElementById("task-list");
  const doneTodayContainer = document.getElementById("done-today-list");
  const completedContainer = document.getElementById("completed-task-list");
  if (!container) {
    return;
  }

  const activeList = Array.isArray(tasks) ? tasks : [];
  const doneTodayList = Array.isArray(doneTodayTasks) ? doneTodayTasks : [];
  const completedList = Array.isArray(completedTasks) ? completedTasks : [];

  const combined = activeList.concat(doneTodayList);
  if (!combined.length) {
    container.innerHTML =
      '<h3>In progress</h3><p class="empty">No tasks yet.</p>';
    tasksState = new Map();
  } else {
    setTasksState(combined);
  }

  if (!activeList.length) {
    container.innerHTML =
      '<h3>In progress</h3><p class="empty">No tasks yet.</p>';
  } else {
    const items = activeList
      .map((task) => {
        const name = escapeHtml(task.name);
        const project = escapeHtml(task.project_name || "Unassigned");
        const time = formatSeconds(task.today_seconds || 0);
        const tooltip =
          task.labels && task.labels.length
            ? `${name} · ${project} · ${task.labels.map((label) => label.name).join(", ")}`
            : `${name} · ${project}`;
        const editFormId = `edit-task-${task.id}`;
        const editField = `<div class="editable-field">
            <span class="name-badge name-task task-title" title="${escapeHtml(tooltip)}">${name}</span>
            <button class="edit-toggle icon-button" type="button" aria-label="Edit task" data-edit-target="${editFormId}">
              <i class="bi bi-pencil"></i>
            </button>
          </div>`;
        const labelOptions = availableLabels
          .map(
            (label) =>
              `<option value="${label.id}">${escapeHtml(label.name)}</option>`,
          )
          .join("");
        return `<li class="task-item">
                  <div class="task-info">
                    ${editField}
                    <form id="${editFormId}" class="edit-form" method="post" action="/tasks/${task.id}/edit">
                      <input type="text" name="name" value="${name}" required />
                      <div class="task-edit-row">
                        <select name="label_id">
                          <option value="" selected>Add label</option>
                          ${labelOptions}
                        </select>
                        <button class="btn btn-outline-secondary btn-sm" type="submit">
                          <i class="bi bi-check2"></i>
                          Save
                        </button>
                      </div>
                    </form>
                    <span class="task-time" data-task-id="${task.id}">${time}</span>
                  </div>
                  <div class="task-actions">
                    <form method="post" action="/tasks/${task.id}/daily-check" data-action="daily-check" data-task-id="${task.id}">
                      <button class="btn btn-outline-success btn-sm menu-item" type="submit" aria-label="Done today">
                        <i class="bi bi-check2-circle"></i>
                      </button>
                    </form>
                    ${task.is_running
                      ? `<form method="post" action="/tasks/${task.id}/stop" data-action="stop" data-task-id="${task.id}">
                           <button class="btn btn-outline-warning btn-sm menu-item danger" type="submit" aria-label="Stop">
                             <i class="bi bi-pause-fill"></i>
                           </button>
                         </form>`
                      : `<form method="post" action="/tasks/${task.id}/start" data-action="start" data-task-id="${task.id}">
                           <button class="btn btn-outline-primary btn-sm menu-item" type="submit" aria-label="Start">
                             <i class="bi bi-play-fill"></i>
                           </button>
                         </form>`}
                    <div class="menu">
                      <button class="menu-button icon-button" type="button" aria-label="More">
                        <i class="bi bi-three-dots"></i>
                      </button>
                      <div class="menu-panel">
                        <button class="menu-item" type="button" data-edit-target="${editFormId}">Edit task</button>
                        <form method="post" action="/tasks/${task.id}/complete" data-action="complete" data-task-id="${task.id}">
                          <button class="menu-item" type="submit">Complete</button>
                        </form>
                        <form method="post" action="/tasks/${task.id}/delete" data-action="delete" data-task-id="${task.id}">
                          <button class="menu-item danger" type="submit">Delete task</button>
                        </form>
                      </div>
                    </div>
                  </div>
                </li>`;
      })
      .join("");

    container.innerHTML = `<h3>In progress</h3><ul class="task-list">${items}</ul>`;
  }

  if (doneTodayContainer) {
    if (!doneTodayList.length) {
      doneTodayContainer.innerHTML =
        '<h3>Done today</h3><p class="empty">No tasks done today.</p>';
    } else {
      const items = doneTodayList
        .map((task) => {
          const name = escapeHtml(task.name);
          const project = escapeHtml(task.project_name || "Unassigned");
          const time = formatSeconds(task.today_seconds || 0);
          const tooltip =
            task.labels && task.labels.length
              ? `${name} · ${project} · ${task.labels.map((label) => label.name).join(", ")}`
              : `${name} · ${project}`;
          const editFormId = `edit-task-${task.id}`;
          const labelOptions = availableLabels
            .map(
              (label) =>
                `<option value="${label.id}">${escapeHtml(label.name)}</option>`,
            )
            .join("");
          return `<li class="task-item is-done-today">
                    <div class="task-info">
                      <div class="editable-field">
                        <span class="name-badge name-task task-title" title="${escapeHtml(tooltip)}">${name}</span>
                        <button class="edit-toggle icon-button" type="button" aria-label="Edit task" data-edit-target="${editFormId}">
                          <i class="bi bi-pencil"></i>
                        </button>
                      </div>
                      <form id="${editFormId}" class="edit-form" method="post" action="/tasks/${task.id}/edit">
                        <input type="text" name="name" value="${name}" required />
                        <div class="task-edit-row">
                          <select name="label_id">
                            <option value="" selected>Add label</option>
                            ${labelOptions}
                          </select>
                          <button class="btn btn-outline-secondary btn-sm" type="submit">
                            <i class="bi bi-check2"></i>
                            Save
                          </button>
                        </div>
                      </form>
                      <span class="task-time" data-task-id="${task.id}">${time}</span>
                    </div>
                    <div class="task-actions">
                      ${task.is_running
                        ? `<form method="post" action="/tasks/${task.id}/stop" data-action="stop" data-task-id="${task.id}">
                             <button class="btn btn-outline-warning btn-sm menu-item danger" type="submit" aria-label="Stop">
                               <i class="bi bi-pause-fill"></i>
                             </button>
                           </form>`
                        : `<form method="post" action="/tasks/${task.id}/start" data-action="start" data-task-id="${task.id}">
                             <button class="btn btn-outline-primary btn-sm menu-item" type="submit" aria-label="Start">
                               <i class="bi bi-play-fill"></i>
                             </button>
                           </form>`}
                      <div class="menu">
                        <button class="menu-button icon-button" type="button" aria-label="More">
                          <i class="bi bi-three-dots"></i>
                        </button>
                        <div class="menu-panel">
                          <button class="menu-item" type="button" data-edit-target="${editFormId}">Edit task</button>
                          <form method="post" action="/tasks/${task.id}/complete" data-action="complete" data-task-id="${task.id}">
                            <button class="menu-item" type="submit">Complete</button>
                          </form>
                          <form method="post" action="/tasks/${task.id}/delete" data-action="delete" data-task-id="${task.id}">
                            <button class="menu-item danger" type="submit">Delete task</button>
                          </form>
                        </div>
                      </div>
                    </div>
                  </li>`;
        })
        .join("");
      doneTodayContainer.innerHTML = `<h3>Done today</h3><ul class="task-list">${items}</ul>`;
    }
  }

  if (completedContainer) {
    if (!completedList.length) {
      completedContainer.innerHTML = '<p class="empty">No completed tasks yet.</p>';
    } else {
      const items = completedList
        .map((task) => {
          const name = escapeHtml(task.name);
          const project = escapeHtml(task.project_name || "Unassigned");
          const time = formatSeconds(task.total_seconds || 0);
          const tooltip =
            task.labels && task.labels.length
              ? `${name} · ${project} · ${task.labels.map((label) => label.name).join(", ")}`
              : `${name} · ${project}`;
          return `<li class="task-item is-completed">
                    <div class="task-info">
                      <div class="editable-field">
                        <span class="name-badge name-task task-title" title="${escapeHtml(tooltip)}">${name}</span>
                      </div>
                      <span class="task-time">${time}</span>
                    </div>
                    <div class="task-actions">
                      <form method="post" action="/tasks/${task.id}/reopen" data-action="reopen" data-task-id="${task.id}">
                        <button class="btn btn-outline-secondary btn-sm menu-item" type="submit">
                          <i class="bi bi-arrow-counterclockwise"></i>
                          Reopen
                        </button>
                      </form>
                      <form method="post" action="/tasks/${task.id}/delete" data-action="delete" data-task-id="${task.id}">
                        <button class="btn btn-outline-danger btn-sm menu-item danger" type="submit">
                          <i class="bi bi-trash"></i>
                          Delete task
                        </button>
                      </form>
                    </div>
                  </li>`;
        })
        .join("");
      completedContainer.innerHTML = `<ul class="task-list">${items}</ul>`;
    }
  }
}

async function createTask(name, projectId, labelIds) {
  const response = await fetch("/api/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, project_id: projectId, label_ids: labelIds }),
  });

  if (!response.ok) {
    throw new Error("Failed to create task");
  }

  const payload = await response.json();
  return {
    tasks: payload.tasks || [],
    doneTodayTasks: payload.done_today_tasks || [],
    completedTasks: payload.completed_tasks || [],
  };
}

async function loadTasks() {
  const response = await fetch("/api/tasks");
  if (!response.ok) {
    throw new Error("Failed to load tasks");
  }
  const payload = await response.json();
  return {
    tasks: payload.tasks || [],
    doneTodayTasks: payload.done_today_tasks || [],
    completedTasks: payload.completed_tasks || [],
  };
}

async function updateTaskState(taskId, action) {
  const response = await fetch(`/api/tasks/${taskId}/${action}`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error("Failed to update task");
  }

  const payload = await response.json();
  return {
    tasks: payload.tasks || [],
    doneTodayTasks: payload.done_today_tasks || [],
    completedTasks: payload.completed_tasks || [],
  };
}

function startLiveTimer() {
  setInterval(() => {
    for (const [taskId, state] of tasksState.entries()) {
      if (!state.isRunning) {
        continue;
      }
      state.todaySeconds = Math.min(86400, state.todaySeconds + 1);
      updateTimeDisplay(taskId, state.todaySeconds);
    }
  }, 1000);
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("task-form");
  const input = document.getElementById("task-name");
  const projectSelect = document.getElementById("task-project");
  const labelsSelect = document.getElementById("task-labels");
  const createLabelToggle = document.getElementById("create-label-toggle");
  const createLabelPicker = document.getElementById("create-label-picker");
  const taskList = document.getElementById("task-list");
  const doneTodayList = document.getElementById("done-today-list");
  const completedTaskList = document.getElementById("completed-task-list");
  const labelToggles = document.querySelectorAll(".label-toggle[data-target]");

  if (form && input) {
    if (createLabelToggle && createLabelPicker) {
      createLabelToggle.addEventListener("click", () => {
        createLabelPicker.classList.toggle("is-open");
      });
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const name = input.value.trim();
      const projectId =
        (projectSelect && projectSelect.value) || form.dataset.projectId;
      const labelIds = labelsSelect
        ? Array.from(labelsSelect.selectedOptions).map((option) => option.value)
        : [];
      if (!name || !projectId) {
        return;
      }

      try {
        const taskPayload = await createTask(name, projectId, labelIds);
        renderTasks(
          taskPayload.tasks,
          taskPayload.doneTodayTasks,
          taskPayload.completedTasks,
        );
        input.value = "";
        input.focus();
        if (labelsSelect) {
          labelsSelect.selectedIndex = -1;
        }
      } catch (error) {
        form.submit();
      }
    });

    loadTasks()
      .then((taskPayload) => {
        renderTasks(
          taskPayload.tasks,
          taskPayload.doneTodayTasks,
          taskPayload.completedTasks,
        );
      })
      .catch(() => {});
    startLiveTimer();
  }

  const bindTaskList = (container) => {
    if (!container) {
      return;
    }
    container.addEventListener("submit", async (event) => {
      const target = event.target;
      if (!(target instanceof HTMLFormElement)) {
        return;
      }

      const action = target.dataset.action;
      const taskId = target.dataset.taskId;
      if (!action || !taskId) {
        return;
      }

      event.preventDefault();
      if (action === "delete" && !window.confirm("Delete this task?")) {
        return;
      }
      try {
        const taskPayload = await updateTaskState(taskId, action);
        renderTasks(
          taskPayload.tasks,
          taskPayload.doneTodayTasks,
          taskPayload.completedTasks,
        );
      } catch (error) {
        target.submit();
      }
    });
  };

  bindTaskList(taskList);
  bindTaskList(doneTodayList);
  bindTaskList(completedTaskList);

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    const menuButton = target.closest(".menu-button");
    if (menuButton) {
      const menu = menuButton.closest(".menu");
      if (!menu) {
        return;
      }
      const panel = menu.querySelector(".menu-panel");
      if (!panel) {
        return;
      }
      document.querySelectorAll(".menu-panel").forEach((el) => {
        if (el !== panel) {
          el.classList.remove("is-open");
        }
      });
      panel.classList.toggle("is-open");
      return;
    }
    if (!target.closest(".menu")) {
      document.querySelectorAll(".menu-panel").forEach((el) => {
        el.classList.remove("is-open");
      });
    }
  });

  labelToggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const targetSelector = toggle.dataset.target;
      if (!targetSelector) {
        return;
      }
      const target = document.querySelector(targetSelector);
      if (target) {
        target.classList.toggle("is-open");
      }
    });
  });

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    const editButton = target.closest("[data-edit-target]");
    if (editButton) {
      event.preventDefault();
      toggleEditForm(editButton.dataset.editTarget);
      return;
    }
    if (!target.closest(".edit-form")) {
      document.querySelectorAll(".edit-form.is-open").forEach((formEl) => {
        formEl.classList.remove("is-open");
      });
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }
    document.querySelectorAll(".edit-form.is-open").forEach((formEl) => {
      formEl.classList.remove("is-open");
    });
  });
});
