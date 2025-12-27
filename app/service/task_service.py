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
        tasks = self.repository.fetch_tasks()
        task_ids = [task["id"] for task in tasks]
        labels_map = self.repository.fetch_task_labels_map(task_ids)
        return [
            {
                **dict(task),
                "labels": labels_map.get(task["id"], []),
            }
            for task in tasks
        ]

    def list_tasks_by_project(self, project_id):
        tasks = self.repository.fetch_tasks_by_project(project_id)
        task_ids = [task["id"] for task in tasks]
        labels_map = self.repository.fetch_task_labels_map(task_ids)
        return [
            {
                **dict(task),
                "labels": labels_map.get(task["id"], []),
            }
            for task in tasks
        ]

    def add_task(self, name, project_id, label_ids=None):
        name = (name or "").strip()
        if name and project_id:
            task_id = self.repository.create_task(
                name, datetime.utcnow().isoformat(), int(project_id)
            )
            for label_id in label_ids or []:
                self.repository.add_label_to_task(task_id, int(label_id))

    def list_projects(self):
        projects = self.repository.fetch_projects()
        project_ids = [project["id"] for project in projects]
        labels_map = self.repository.fetch_project_labels_map(project_ids)
        return [
            {
                **dict(project),
                "labels": labels_map.get(project["id"], []),
            }
            for project in projects
        ]

    def get_project(self, project_id):
        project = self.repository.fetch_project(project_id)
        if project is None:
            return None
        labels_map = self.repository.fetch_project_labels_map([project["id"]])
        return {
            **dict(project),
            "labels": labels_map.get(project["id"], []),
        }

    def add_project(self, name, label_ids=None):
        name = (name or "").strip()
        if name:
            project_id = self.repository.create_project(
                name, datetime.utcnow().isoformat()
            )
            for label_id in label_ids or []:
                self.repository.add_label_to_project(project_id, int(label_id))

    def delete_project(self, project_id):
        self.repository.delete_project(project_id)

    def list_labels(self):
        labels = self.repository.fetch_labels()
        return [dict(label) for label in labels]

    def add_label(self, name, color):
        name = (name or "").strip()
        color = (color or "").strip()
        if name and color:
            self.repository.create_label(name, color, datetime.utcnow().isoformat())

    def delete_label(self, label_id):
        self.repository.delete_label(label_id)

    def add_label_to_task(self, task_id, label_id):
        self.repository.add_label_to_task(task_id, label_id)

    def add_label_to_project(self, project_id, label_id):
        self.repository.add_label_to_project(project_id, label_id)

    def start_task(self, task_id):
        if not self.repository.is_task_running(task_id):
            self.repository.start_task(task_id, datetime.utcnow().isoformat())

    def stop_task(self, task_id):
        self.repository.stop_task(task_id, datetime.utcnow().isoformat())

    def delete_task(self, task_id):
        self.repository.delete_task(task_id)
