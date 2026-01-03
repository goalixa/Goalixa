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
              <span class="label-chip" style="background-color: ${safeColor}">${safeName}</span>
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

function renderTasks(tasks, completedTasks) {
  const container = document.getElementById("task-list");
  const completedContainer = document.getElementById("completed-task-list");
  if (!container) {
    return;
  }

  const activeList = Array.isArray(tasks) ? tasks : [];
  const completedList = Array.isArray(completedTasks) ? completedTasks : [];

  if (!activeList.length) {
    container.innerHTML = '<p class="empty">No tasks yet.</p>';
    tasksState = new Map();
  } else {
    setTasksState(activeList);
    const items = activeList
      .map((task) => {
        const name = escapeHtml(task.name);
        const project = escapeHtml(task.project_name || "Unassigned");
        const time = formatSeconds(task.today_seconds || 0);
        const dailyChecks = Number(task.daily_checks || 0);
        const labels = renderLabelChips(task.labels || [], `task-${task.id}`);
        const editFormId = `edit-task-${task.id}`;
        const editField = `<div class="editable-field">
            <span class="name-badge name-task">${name}</span>
            <button class="edit-toggle icon-button" type="button" aria-label="Edit task" data-edit-target="${editFormId}">
              <i class="bi bi-pencil"></i>
            </button>
          </div>`;
        const editForm = `<form id="${editFormId}" class="edit-form" method="post" action="/tasks/${task.id}/edit">
            <input type="text" name="name" value="${name}" required />
            <button class="btn btn-outline-secondary btn-sm" type="submit">
              <i class="bi bi-check2"></i>
              Save
            </button>
          </form>`;
        const startStop = task.is_running
          ? `<form method="post" action="/tasks/${task.id}/stop" data-action="stop" data-task-id="${task.id}">
               <button class="btn btn-outline-warning btn-sm menu-item danger" type="submit">
                 <i class="bi bi-pause-fill"></i>
                 Stop
               </button>
             </form>`
          : `<form method="post" action="/tasks/${task.id}/start" data-action="start" data-task-id="${task.id}">
               <button class="btn btn-outline-primary btn-sm menu-item" type="submit">
                 <i class="bi bi-play-fill"></i>
                 Start
               </button>
             </form>`;
        const labelForm = availableLabels.length
          ? `<form class="label-form" method="post" action="/tasks/${task.id}/labels">
               <select name="label_id" required>
                 <option value="" disabled selected>Add label</option>
                 ${availableLabels
                   .map(
                     (label) =>
                       `<option value="${label.id}">${escapeHtml(label.name)}</option>`,
                   )
                   .join("")}
               </select>
               <button class="btn btn-outline-secondary btn-sm menu-item" type="submit">
                 <i class="bi bi-plus-lg"></i>
                 Add
               </button>
             </form>`
          : "";
        return `<li class="task-item">
                  <div class="task-info">
                    ${editField}
                    <span class="task-project">${project}</span>
                    ${labels}
                    ${editForm}
                    <span class="task-time" data-task-id="${task.id}">${time}</span>
                    <span class="task-meta">Daily checks: ${dailyChecks}</span>
                  </div>
                  <div class="task-actions">
                    <form method="post" action="/tasks/${task.id}/daily-check" data-action="daily-check" data-task-id="${task.id}">
                      <button class="btn btn-outline-success btn-sm menu-item" type="submit">
                        <i class="bi bi-check2-circle"></i>
                        Done today
                      </button>
                    </form>
                    ${startStop}
                    <form method="post" action="/tasks/${task.id}/complete" data-action="complete" data-task-id="${task.id}">
                      <button class="btn btn-outline-secondary btn-sm menu-item" type="submit">
                        <i class="bi bi-check2"></i>
                        Complete
                      </button>
                    </form>
                    <form method="post" action="/tasks/${task.id}/delete" data-action="delete" data-task-id="${task.id}">
                      <button class="btn btn-outline-danger btn-sm menu-item danger" type="submit">
                        <i class="bi bi-trash"></i>
                        Delete task
                      </button>
                    </form>
                    ${labelForm}
                  </div>
                </li>`;
      })
      .join("");

    container.innerHTML = `<ul class="task-list">${items}</ul>`;
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
          const dailyChecks = Number(task.daily_checks || 0);
          const labels = renderLabelChips(task.labels || [], `completed-${task.id}`);
          return `<li class="task-item is-completed">
                    <div class="task-info">
                      <div class="editable-field">
                        <span class="name-badge name-task">${name}</span>
                      </div>
                      <span class="task-project">${project}</span>
                      ${labels}
                      <span class="task-time">${time}</span>
                      <span class="task-meta">Daily checks: ${dailyChecks}</span>
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
        renderTasks(taskPayload.tasks, taskPayload.completedTasks);
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
        renderTasks(taskPayload.tasks, taskPayload.completedTasks);
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
        renderTasks(taskPayload.tasks, taskPayload.completedTasks);
      } catch (error) {
        target.submit();
      }
    });
  };

  bindTaskList(taskList);
  bindTaskList(completedTaskList);

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
