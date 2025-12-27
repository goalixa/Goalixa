from datetime import datetime


class TaskService:
    def __init__(self, repository):
        self.repository = repository

    def init_db(self):
        self.repository.init_db()

    def list_tasks(self):
        return self.repository.fetch_tasks()

    def add_task(self, name):
        name = (name or "").strip()
        if name:
            self.repository.create_task(name, datetime.utcnow().isoformat())

    def start_task(self, task_id):
        if not self.repository.is_task_running(task_id):
            self.repository.start_task(task_id, datetime.utcnow().isoformat())

    def stop_task(self, task_id):
        self.repository.stop_task(task_id, datetime.utcnow().isoformat())

    def delete_task(self, task_id):
        self.repository.delete_task(task_id)
