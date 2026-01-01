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
        rollingSeconds: Number(task.rolling_24h_seconds || 0),
        isRunning: Boolean(task.is_running),
      },
    ]),
  );
}

function updateTimeDisplay(taskId, rollingSeconds) {
  const timeEl = document.querySelector(`.task-time[data-task-id="${taskId}"]`);
  if (timeEl) {
    timeEl.textContent = formatSeconds(rollingSeconds);
  }
}

function renderLabelChips(labels) {
  if (!labels || !labels.length) {
    return "";
  }
  return `<div class="label-list">
    ${labels
      .map(
        (label) =>
          `<span class="label-chip" style="background-color: ${escapeHtml(label.color)}">${escapeHtml(label.name)}</span>`,
      )
      .join("")}
  </div>`;
}

function renderTasks(tasks) {
  const container = document.getElementById("task-list");
  if (!container) {
    return;
  }

  if (!tasks.length) {
    container.innerHTML = '<p class="empty">No tasks yet.</p>';
    tasksState = new Map();
    return;
  }

  setTasksState(tasks);
  const items = tasks
    .map((task) => {
      const name = escapeHtml(task.name);
      const project = escapeHtml(task.project_name || "Unassigned");
      const time = formatSeconds(task.rolling_24h_seconds || 0);
      const labels = renderLabelChips(task.labels || []);
      const editForm = `<form class="task-form" method="post" action="/tasks/${task.id}/edit">
          <input type="text" name="name" value="${name}" required />
          <button class="btn btn-outline-secondary btn-sm" type="submit">
            <i class="bi bi-pencil"></i>
            Update
          </button>
        </form>`;
      const action = task.is_running
        ? `<form method="post" action="/tasks/${task.id}/stop" data-action="stop" data-task-id="${task.id}">
             <button class="stop icon-button" type="submit" aria-label="Pause">⏸</button>
           </form>`
        : `<form method="post" action="/tasks/${task.id}/start" data-action="start" data-task-id="${task.id}">
             <button class="start icon-button" type="submit" aria-label="Resume">▶</button>
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
             <button type="submit">Add</button>
           </form>`
        : "";
      const menu = `<div class="menu">
          <button class="menu-button icon-button" type="button" aria-label="More">⋯</button>
          <div class="menu-panel">
            <form method="post" action="/tasks/${task.id}/delete" data-action="delete" data-task-id="${task.id}">
              <button class="menu-item danger" type="submit">Delete task</button>
            </form>
            ${labelForm}
          </div>
        </div>`;
      return `<li class="task-item">
                <div class="task-info">
                  <span class="name-badge name-task">${name}</span>
                  <span class="task-project">${project}</span>
                  ${labels}
                  ${editForm}
                  <span class="task-time" data-task-id="${task.id}">${time}</span>
                </div>
                <div class="task-actions">
                  ${action}
                  ${menu}
                </div>
              </li>`;
    })
    .join("");

  container.innerHTML = `<ul class="task-list">${items}</ul>`;
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
  return payload.tasks || [];
}

async function loadTasks() {
  const response = await fetch("/api/tasks");
  if (!response.ok) {
    throw new Error("Failed to load tasks");
  }
  const payload = await response.json();
  return payload.tasks || [];
}

async function updateTaskState(taskId, action) {
  const response = await fetch(`/api/tasks/${taskId}/${action}`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error("Failed to update task");
  }

  const payload = await response.json();
  return payload.tasks || [];
}

function startLiveTimer() {
  setInterval(() => {
    for (const [taskId, state] of tasksState.entries()) {
      if (!state.isRunning) {
        continue;
      }
      state.rollingSeconds = Math.min(86400, state.rollingSeconds + 1);
      updateTimeDisplay(taskId, state.rollingSeconds);
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
        const tasks = await createTask(name, projectId, labelIds);
        renderTasks(tasks);
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
      .then(renderTasks)
      .catch(() => {});
    startLiveTimer();
  }

  if (taskList) {
    taskList.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      if (target.classList.contains("menu-button")) {
        const menu = target.closest(".menu");
        if (!menu) {
          return;
        }
        const panel = menu.querySelector(".menu-panel");
        if (!panel) {
          return;
        }
        taskList.querySelectorAll(".menu-panel").forEach((el) => {
          if (el !== panel) {
            el.classList.remove("is-open");
          }
        });
        panel.classList.toggle("is-open");
      } else if (!target.closest(".menu")) {
        taskList.querySelectorAll(".menu-panel").forEach((el) => {
          el.classList.remove("is-open");
        });
      }
    });

    taskList.addEventListener("submit", async (event) => {
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
        const tasks = await updateTaskState(taskId, action);
        renderTasks(tasks);
      } catch (error) {
        target.submit();
      }
    });
  }

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
});
