from datetime import datetime


class TaskService:
    def __init__(self, repository):
        self.repository = repository

    def init_db(self):
        self.repository.init_db()
        default_project_id = self.repository.ensure_default_project(
            "General", datetime.utcnow().isoformat()
        )
        if default_project_id:
            self.repository.backfill_tasks_project(default_project_id)

    def list_tasks(self):
        return self.repository.fetch_tasks()

    def list_tasks_by_project(self, project_id):
        return self.repository.fetch_tasks_by_project(project_id)

    def add_task(self, name, project_id):
        name = (name or "").strip()
        if name and project_id:
            self.repository.create_task(
                name, datetime.utcnow().isoformat(), int(project_id)
            )

    def list_projects(self):
        return self.repository.fetch_projects()

    def get_project(self, project_id):
        return self.repository.fetch_project(project_id)

    def add_project(self, name):
        name = (name or "").strip()
        if name:
            self.repository.create_project(name, datetime.utcnow().isoformat())

    def delete_project(self, project_id):
        self.repository.delete_project(project_id)

    def start_task(self, task_id):
        if not self.repository.is_task_running(task_id):
            self.repository.start_task(task_id, datetime.utcnow().isoformat())

    def stop_task(self, task_id):
        self.repository.stop_task(task_id, datetime.utcnow().isoformat())

    def delete_task(self, task_id):
        self.repository.delete_task(task_id)
