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
      const time = formatSeconds(task.total_seconds || 0);
      const action = task.is_running
        ? `<form method="post" action="/tasks/${task.id}/stop" data-action="stop" data-task-id="${task.id}">
             <button class="stop" type="submit">Stop</button>
           </form>`
        : `<form method="post" action="/tasks/${task.id}/start" data-action="start" data-task-id="${task.id}">
             <button class="start" type="submit">Start</button>
           </form>`;
      const remove = `<form method="post" action="/tasks/${task.id}/delete" data-action="delete" data-task-id="${task.id}">
                        <button class="delete" type="submit">Delete</button>
                      </form>`;
      return `<li class="task-item">
                <div class="task-info">
                  <span class="task-name">${name}</span>
                  <span class="task-time" data-task-id="${task.id}">${time}</span>
                </div>
                <div class="task-actions">
                  ${action}
                  ${remove}
                </div>
              </li>`;
    })
    .join("");

  container.innerHTML = `<ul class="task-list">${items}</ul>`;
}

async function createTask(name) {
  const response = await fetch("/api/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
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
  const taskList = document.getElementById("task-list");
  if (!form || !input) {
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = input.value.trim();
    if (!name) {
      return;
    }

    try {
      const tasks = await createTask(name);
      renderTasks(tasks);
      input.value = "";
      input.focus();
    } catch (error) {
      form.submit();
    }
  });

  loadTasks()
    .then(renderTasks)
    .catch(() => {});
  startLiveTimer();

  if (taskList) {
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
