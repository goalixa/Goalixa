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

    def project_distribution_by_range(self, start_date, end_date):
        start_day = datetime.combine(start_date, datetime.min.time())
        end_day = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
        entries = self.repository.fetch_time_entries_with_projects_between(
            start_day.isoformat(), end_day.isoformat()
        )

        totals = {}
        for entry in entries:
            entry_start = datetime.fromisoformat(entry["started_at"])
            entry_end = (
                datetime.fromisoformat(entry["ended_at"])
                if entry["ended_at"]
                else datetime.utcnow()
            )
            overlap_start = max(entry_start, start_day)
            overlap_end = min(entry_end, end_day)
            if overlap_end <= overlap_start:
                continue
            seconds = int((overlap_end - overlap_start).total_seconds())
            project_name = entry["project_name"] or "Unassigned"
            totals[project_name] = totals.get(project_name, 0) + seconds

        total_seconds = sum(totals.values())
        distribution = []
        for project_name, seconds in totals.items():
            percent = (seconds / total_seconds) * 100 if total_seconds else 0
            distribution.append(
                {
                    "project": project_name,
                    "seconds": seconds,
                    "percent": percent,
                }
            )
        distribution.sort(key=lambda item: item["seconds"], reverse=True)
        return distribution, total_seconds

    def distribution_by_range(self, start_date, end_date, group_by):
        start_day = datetime.combine(start_date, datetime.min.time())
        end_day = datetime.combine(end_date + timedelta(days=1), datetime.min.time())

        if group_by == "tasks":
            entries = self.repository.fetch_time_entries_with_tasks_between(
                start_day.isoformat(), end_day.isoformat()
            )
            name_key = "task_name"
            fallback = "Unnamed Task"
        elif group_by == "labels":
            entries = self.repository.fetch_time_entries_with_labels_between(
                start_day.isoformat(), end_day.isoformat()
            )
            name_key = "label_name"
            fallback = "Unlabeled"
        else:
            entries = self.repository.fetch_time_entries_with_projects_between(
                start_day.isoformat(), end_day.isoformat()
            )
            name_key = "project_name"
            fallback = "Unassigned"

        totals = {}
        for entry in entries:
            entry_start = datetime.fromisoformat(entry["started_at"])
            entry_end = (
                datetime.fromisoformat(entry["ended_at"])
                if entry["ended_at"]
                else datetime.utcnow()
            )
            overlap_start = max(entry_start, start_day)
            overlap_end = min(entry_end, end_day)
            if overlap_end <= overlap_start:
                continue
            seconds = int((overlap_end - overlap_start).total_seconds())
            label = entry[name_key] or fallback
            totals[label] = totals.get(label, 0) + seconds

        total_seconds = sum(totals.values())
        distribution = []
        for label, seconds in totals.items():
            percent = (seconds / total_seconds) * 100 if total_seconds else 0
            distribution.append(
                {
                    "label": label,
                    "seconds": seconds,
                    "percent": percent,
                }
            )
        distribution.sort(key=lambda item: item["seconds"], reverse=True)
        return distribution, total_seconds

    def list_time_entries_by_range(self, start_date, end_date):
        start_day = datetime.combine(start_date, datetime.min.time())
        end_day = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
        entries = self.repository.fetch_time_entries_with_task_details_between(
            start_day.isoformat(), end_day.isoformat()
        )
        task_ids = {entry["task_id"] for entry in entries}
        task_id_list = list(task_ids)
        labels_map = self.repository.fetch_task_labels_map(task_id_list)
        running_map = {
            task_id: self.repository.is_task_running(task_id)
            for task_id in task_id_list
        }

        days = (end_date - start_date).days + 1
        buckets = []
        today = datetime.utcnow().date()
        for day_offset in range(days):
            day_start = start_day + timedelta(days=day_offset)
            day_end = day_start + timedelta(days=1)
            if day_start.date() == today:
                label = "Today"
            elif day_start.date() == (today - timedelta(days=1)):
                label = "Yesterday"
            else:
                label = day_start.strftime("%a, %d %b")
            buckets.append(
                {
                    "label": label,
                    "start": day_start,
                    "end": day_end,
                    "entries": [],
                    "total_seconds": 0,
                }
            )

        now = datetime.utcnow()
        for entry in entries:
            entry_start = datetime.fromisoformat(entry["started_at"])
            entry_end = (
                datetime.fromisoformat(entry["ended_at"])
                if entry["ended_at"]
                else now
            )
            entry_labels = [
                label["name"] for label in labels_map.get(entry["task_id"], [])
            ]
            for bucket in buckets:
                overlap_start = max(entry_start, bucket["start"])
                overlap_end = min(entry_end, bucket["end"])
                if overlap_end <= overlap_start:
                    continue
                duration = int((overlap_end - overlap_start).total_seconds())
                bucket["total_seconds"] += duration
                bucket["entries"].append(
                    {
                        "task_id": entry["task_id"],
                        "task_name": entry["task_name"] or "Unnamed Task",
                        "project_name": entry["project_name"] or "Unassigned",
                        "labels": entry_labels,
                        "duration_seconds": duration,
                        "start_time": self._format_time(overlap_start),
                        "end_time": self._format_time(overlap_end),
                        "is_running": bool(running_map.get(entry["task_id"], False)),
                        "sort_ts": overlap_start.timestamp(),
                    }
                )

        result = []
        for bucket in buckets:
            if not bucket["entries"]:
                continue
            bucket["entries"].sort(key=lambda item: item["sort_ts"], reverse=True)
            for item in bucket["entries"]:
                item.pop("sort_ts", None)
            bucket.pop("start", None)
            bucket.pop("end", None)
            result.append(bucket)

        return result

    def list_time_entries_for_calendar(self, start_dt, end_dt):
        entries = self.repository.fetch_time_entries_with_task_details_between(
            start_dt.isoformat(), end_dt.isoformat()
        )
        now = datetime.utcnow()
        palette = [
            ("#fef3c7", "#f59e0b", "#7c2d12"),
            ("#dbeafe", "#2563eb", "#1e3a8a"),
            ("#dcfce7", "#16a34a", "#14532d"),
            ("#fae8ff", "#9333ea", "#4a044e"),
            ("#ffe4e6", "#e11d48", "#881337"),
            ("#e0f2fe", "#0284c7", "#0c4a6e"),
        ]
        events = []
        for entry in entries:
            entry_start = datetime.fromisoformat(entry["started_at"])
            entry_end = (
                datetime.fromisoformat(entry["ended_at"])
                if entry["ended_at"]
                else now
            )
            overlap_start = max(entry_start, start_dt)
            overlap_end = min(entry_end, end_dt)
            if overlap_end <= overlap_start:
                continue
            task_name = entry["task_name"] or "Unnamed Task"
            project_name = entry["project_name"] or "Unassigned"
            title = f"{task_name} · {project_name}" if project_name else task_name
            colors = palette[entry["task_id"] % len(palette)]
            events.append(
                {
                    "title": title,
                    "start": overlap_start.isoformat(),
                    "end": overlap_end.isoformat(),
                    "taskId": entry["task_id"],
                    "backgroundColor": colors[0],
                    "borderColor": colors[1],
                    "textColor": colors[2],
                }
            )
        return events

    @staticmethod
    def _format_time(value):
        return value.strftime("%I:%M %p").lstrip("0")

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
