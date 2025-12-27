function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

function formatSeconds(totalSeconds) {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
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
        totalSeconds: Number(task.total_seconds || 0),
        isRunning: Boolean(task.is_running),
      },
    ]),
  );
}

function updateTimeDisplay(taskId, totalSeconds) {
  const timeEl = document.querySelector(`.task-time[data-task-id="${taskId}"]`);
  if (timeEl) {
    timeEl.textContent = formatSeconds(totalSeconds);
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
      const time = formatSeconds(task.total_seconds || 0);
      const labels = renderLabelChips(task.labels || []);
      const action = task.is_running
        ? `<form method="post" action="/tasks/${task.id}/stop" data-action="stop" data-task-id="${task.id}">
             <button class="stop icon-button" type="submit" aria-label="Pause">⏸</button>
           </form>`
        : `<form method="post" action="/tasks/${task.id}/start" data-action="start" data-task-id="${task.id}">
             <button class="start icon-button" type="submit" aria-label="Resume">▶</button>
           </form>`;
      const remove = `<form method="post" action="/tasks/${task.id}/delete" data-action="delete" data-task-id="${task.id}">
                        <button class="delete icon-button" type="submit" aria-label="Delete">×</button>
                      </form>`;
      const labelToggle = `<button class="label-toggle icon-button" type="button" data-task-id="${task.id}" aria-label="Labels">🏷️</button>`;
      const labelForm = availableLabels.length
        ? `<div class="label-picker" data-task-id="${task.id}">
             <form class="label-form" method="post" action="/tasks/${task.id}/labels">
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
             </form>
           </div>`
        : "";
      return `<li class="task-item">
                <div class="task-info">
                  <span class="task-name">${name}</span>
                  <span class="task-project">${project}</span>
                  ${labels}
                  <span class="task-time" data-task-id="${task.id}">${time}</span>
                </div>
                <div class="task-actions">
                  ${action}
                  ${remove}
                  ${labelToggle}
                </div>
                ${labelForm}
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
      state.totalSeconds += 1;
      updateTimeDisplay(taskId, state.totalSeconds);
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
      if (!target.classList.contains("label-toggle")) {
        return;
      }
      const taskId = target.dataset.taskId;
      const picker = taskList.querySelector(
        `.label-picker[data-task-id="${taskId}"]`,
      );
      if (picker) {
        picker.classList.toggle("is-open");
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
});
