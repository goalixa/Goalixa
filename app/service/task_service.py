from datetime import datetime, timedelta


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

    def summary_by_days(self, days):
        days = int(days)
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        start_day = (now - timedelta(days=days - 1)).replace(hour=0)
        end_day = (now + timedelta(days=1)).replace(hour=0)

        entries = self.repository.fetch_time_entries_between(
            start_day.isoformat(), end_day.isoformat()
        )

        buckets = []
        for day_offset in range(days):
            day_start = start_day + timedelta(days=day_offset)
            day_end = day_start + timedelta(days=1)
            buckets.append(
                {
                    "date": day_start.date().isoformat(),
                    "label": day_start.strftime("%d %b"),
                    "start": day_start,
                    "end": day_end,
                    "seconds": 0,
                }
            )

        for entry in entries:
            entry_start = datetime.fromisoformat(entry["started_at"])
            entry_end = (
                datetime.fromisoformat(entry["ended_at"])
                if entry["ended_at"]
                else datetime.utcnow()
            )
            for bucket in buckets:
                overlap_start = max(entry_start, bucket["start"])
                overlap_end = min(entry_end, bucket["end"])
                if overlap_end > overlap_start:
                    bucket["seconds"] += int(
                        (overlap_end - overlap_start).total_seconds()
                    )

        max_seconds = max((bucket["seconds"] for bucket in buckets), default=0)
        for bucket in buckets:
            bucket["percent"] = (
                int((bucket["seconds"] / max_seconds) * 100)
                if max_seconds
                else 0
            )
            del bucket["start"]
            del bucket["end"]

        return buckets

    def summary_by_range(self, start_date, end_date):
        start_day = datetime.combine(start_date, datetime.min.time())
        end_day = datetime.combine(end_date + timedelta(days=1), datetime.min.time())

        entries = self.repository.fetch_time_entries_between(
            start_day.isoformat(), end_day.isoformat()
        )

        days = (end_date - start_date).days + 1
        buckets = []
        for day_offset in range(days):
            day_start = start_day + timedelta(days=day_offset)
            day_end = day_start + timedelta(days=1)
            buckets.append(
                {
                    "date": day_start.date().isoformat(),
                    "label": day_start.strftime("%d %b"),
                    "start": day_start,
                    "end": day_end,
                    "seconds": 0,
                }
            )

        for entry in entries:
            entry_start = datetime.fromisoformat(entry["started_at"])
            entry_end = (
                datetime.fromisoformat(entry["ended_at"])
                if entry["ended_at"]
                else datetime.utcnow()
            )
            for bucket in buckets:
                overlap_start = max(entry_start, bucket["start"])
                overlap_end = min(entry_end, bucket["end"])
                if overlap_end > overlap_start:
                    bucket["seconds"] += int(
                        (overlap_end - overlap_start).total_seconds()
                    )

        max_seconds = max((bucket["seconds"] for bucket in buckets), default=0)
        for bucket in buckets:
            bucket["percent"] = (
                int((bucket["seconds"] / max_seconds) * 100)
                if max_seconds
                else 0
            )
            del bucket["start"]
            del bucket["end"]

        return buckets

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
