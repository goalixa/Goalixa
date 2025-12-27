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

function renderTasks(tasks) {
  const container = document.getElementById("task-list");
  if (!container) {
    return;
  }

  if (!tasks.length) {
    container.innerHTML = '<p class="empty">No tasks yet.</p>';
    return;
  }

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
      return `<li class="task-item">
                <div class="task-info">
                  <span class="task-name">${name}</span>
                  <span class="task-time">${time}</span>
                </div>
                <div class="task-actions">
                  ${action}
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
      try {
        const tasks = await updateTaskState(taskId, action);
        renderTasks(tasks);
      } catch (error) {
        target.submit();
      }
    });
  }
});
