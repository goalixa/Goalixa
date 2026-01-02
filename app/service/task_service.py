from datetime import datetime, timedelta


class TaskService:
    def __init__(self, repository):
        self.repository = repository

    def _parse_subgoals(self, raw_value):
        lines = (raw_value or "").splitlines()
        cleaned = []
        for line in lines:
            title = line.strip()
            if title:
                cleaned.append(title)
        return cleaned

    def _habit_streak(self, done_dates, today):
        if not done_dates:
            return 0
        cursor = today
        if cursor.isoformat() not in done_dates:
            cursor = today - timedelta(days=1)
        streak = 0
        while cursor.isoformat() in done_dates:
            streak += 1
            cursor = cursor - timedelta(days=1)
        return streak

    def _most_common(self, values, fallback=""):
        if not values:
            return fallback
        counts = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        return max(counts.items(), key=lambda item: item[1])[0]

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

    def update_task(self, task_id, name):
        name = (name or "").strip()
        if name:
            self.repository.update_task(int(task_id), name)

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

    def update_project(self, project_id, name):
        name = (name or "").strip()
        if name:
            self.repository.update_project(int(project_id), name)

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

    def update_label(self, label_id, name, color):
        name = (name or "").strip()
        color = (color or "").strip()
        if name and color:
            self.repository.update_label(int(label_id), name, color)

    def delete_label(self, label_id):
        self.repository.delete_label(label_id)

    def add_label_to_task(self, task_id, label_id):
        self.repository.add_label_to_task(task_id, label_id)

    def add_label_to_project(self, project_id, label_id):
        self.repository.add_label_to_project(project_id, label_id)

    def list_goals(self):
        goals = self.repository.fetch_goals()
        if not goals:
            return []
        goal_ids = [goal["id"] for goal in goals]
        goal_projects_map = self.repository.fetch_goal_projects(goal_ids)
        goal_tasks_map = self.repository.fetch_goal_tasks(goal_ids)
        goal_subgoals_map = self.repository.fetch_goal_subgoals(goal_ids)

        project_ids = sorted(
            {pid for ids in goal_projects_map.values() for pid in ids}
        )
        projects = self.repository.fetch_projects_by_ids(project_ids)
        projects_by_id = {project["id"]: dict(project) for project in projects}

        task_ids = sorted({tid for ids in goal_tasks_map.values() for tid in ids})
        if project_ids:
            project_tasks = self.repository.fetch_tasks_by_project_ids(project_ids)
            for task in project_tasks:
                task_ids.append(task["id"])
        task_ids = sorted(set(task_ids))

        task_totals = self.repository.fetch_task_total_seconds(task_ids)

        goal_list = []
        for goal in goals:
            goal_id = goal["id"]
            direct_task_ids = goal_tasks_map.get(goal_id, [])
            linked_project_ids = goal_projects_map.get(goal_id, [])
            linked_task_ids = set(direct_task_ids)
            if linked_project_ids:
                for task in self.repository.fetch_tasks_by_project_ids(linked_project_ids):
                    linked_task_ids.add(task["id"])

            linked_task_ids = sorted(linked_task_ids)
            total_seconds = sum(task_totals.get(task_id, 0) for task_id in linked_task_ids)
            target_seconds = int(goal["target_seconds"] or 0)
            progress = int((total_seconds / target_seconds) * 100) if target_seconds else 0
            progress = min(progress, 100)

            goal_list.append(
                {
                    **dict(goal),
                    "project_ids": linked_project_ids,
                    "task_ids": direct_task_ids,
                    "projects": [projects_by_id[pid] for pid in linked_project_ids if pid in projects_by_id],
                    "subgoals": goal_subgoals_map.get(goal_id, []),
                    "subgoals_count": len(goal_subgoals_map.get(goal_id, [])),
                    "total_seconds": total_seconds,
                    "progress": progress,
                    "tasks_count": len(linked_task_ids),
                    "projects_count": len(linked_project_ids),
                }
            )
        return goal_list

    def get_goal(self, goal_id):
        goal = self.repository.fetch_goal(goal_id)
        if goal is None:
            return None
        goals = self.list_goals()
        for item in goals:
            if item["id"] == goal_id:
                return item
        return dict(goal)

    def add_goal(
        self,
        name,
        description,
        status,
        priority,
        target_date,
        target_hours,
        subgoals_text=None,
        project_ids=None,
        task_ids=None,
    ):
        name = (name or "").strip()
        description = (description or "").strip()
        status = (status or "active").strip()
        priority = (priority or "medium").strip()
        target_date = (target_date or "").strip() or None
        target_seconds = int(float(target_hours or 0) * 3600)
        subgoals = self._parse_subgoals(subgoals_text)
        if not name:
            return
        created_at = datetime.utcnow().isoformat()
        goal_id = self.repository.create_goal(
            name,
            description,
            status,
            priority,
            target_date,
            target_seconds,
            created_at,
        )
        filtered_project_ids = [int(pid) for pid in project_ids or [] if str(pid).strip()]
        filtered_task_ids = [int(tid) for tid in task_ids or [] if str(tid).strip()]
        self.repository.set_goal_projects(goal_id, filtered_project_ids)
        self.repository.set_goal_tasks(goal_id, filtered_task_ids)
        self.repository.set_goal_subgoals(goal_id, subgoals, created_at)

    def update_goal(
        self,
        goal_id,
        name,
        description,
        status,
        priority,
        target_date,
        target_hours,
        subgoals_text=None,
        project_ids=None,
        task_ids=None,
    ):
        name = (name or "").strip()
        description = (description or "").strip()
        status = (status or "active").strip()
        priority = (priority or "medium").strip()
        target_date = (target_date or "").strip() or None
        target_seconds = int(float(target_hours or 0) * 3600)
        subgoals = self._parse_subgoals(subgoals_text)
        if not name:
            return
        self.repository.update_goal(
            int(goal_id),
            name,
            description,
            status,
            priority,
            target_date,
            target_seconds,
        )
        filtered_project_ids = [int(pid) for pid in project_ids or [] if str(pid).strip()]
        filtered_task_ids = [int(tid) for tid in task_ids or [] if str(tid).strip()]
        self.repository.set_goal_projects(int(goal_id), filtered_project_ids)
        self.repository.set_goal_tasks(int(goal_id), filtered_task_ids)
        self.repository.set_goal_subgoals(int(goal_id), subgoals, datetime.utcnow().isoformat())

    def delete_goal(self, goal_id):
        self.repository.delete_goal(goal_id)

    def start_task(self, task_id):
        if not self.repository.is_task_running(task_id):
            self.repository.start_task(task_id, datetime.utcnow().isoformat())

    def stop_task(self, task_id):
        self.repository.stop_task(task_id, datetime.utcnow().isoformat())

    def delete_task(self, task_id):
        self.repository.delete_task(task_id)

    def list_habits(self, log_date):
        habits = self.repository.fetch_habits()
        if not habits:
            return []
        habit_ids = [habit["id"] for habit in habits]
        done_today = self.repository.fetch_habit_logs_for_date(habit_ids, log_date)
        logs_map = self.repository.fetch_habit_logs_map(habit_ids)
        today = datetime.fromisoformat(log_date).date()
        habit_list = []
        for habit in habits:
            habit_id = habit["id"]
            done_dates = logs_map.get(habit_id, set())
            streak = self._habit_streak(done_dates, today)
            meta_parts = [habit["frequency"]]
            if habit["time_of_day"]:
                meta_parts.append(habit["time_of_day"])
            if habit["goal_name"]:
                meta_parts.append(f"Goal: {habit['goal_name']}")
            if habit["subgoal_name"]:
                meta_parts.append(f"Sub-goal: {habit['subgoal_name']}")
            habit_list.append(
                {
                    **dict(habit),
                    "done": habit_id in done_today,
                    "streak": streak,
                    "meta": " • ".join(meta_parts),
                }
            )
        return habit_list

    def habits_summary(self, habits):
        completed = sum(1 for habit in habits if habit.get("done"))
        total = len(habits)
        best_streak = max((habit.get("streak", 0) for habit in habits), default=0)
        focus_window = self._most_common(
            [habit.get("time_of_day") for habit in habits if habit.get("time_of_day")],
            fallback="Night close",
        )
        return {
            "completed": completed,
            "total": total,
            "best_streak": best_streak,
            "focus_window": focus_window,
        }

    def habit_completion_series(self, days=14):
        today = datetime.utcnow().date()
        start_date = today - timedelta(days=days - 1)
        date_labels = [
            (start_date + timedelta(days=offset)).isoformat() for offset in range(days)
        ]
        habits = self.repository.fetch_habits()
        total_habits = len(habits)
        counts = self.repository.fetch_habit_log_counts(
            start_date.isoformat(), today.isoformat()
        )
        values = []
        for date_label in date_labels:
            done_count = counts.get(date_label, 0)
            percent = int((done_count / total_habits) * 100) if total_habits else 0
            values.append(percent)
        return {
            "labels": date_labels,
            "values": values,
        }

    def add_habit(self, name, frequency, time_of_day, reminder, notes, goal_name, subgoal_name):
        name = (name or "").strip()
        frequency = (frequency or "Daily").strip()
        time_of_day = (time_of_day or "").strip() or None
        reminder = (reminder or "").strip() or None
        notes = (notes or "").strip() or None
        goal_name = (goal_name or "").strip() or None
        subgoal_name = (subgoal_name or "").strip() or None
        if not name:
            return
        self.repository.create_habit(
            name,
            frequency,
            time_of_day,
            reminder,
            notes,
            goal_name,
            subgoal_name,
            datetime.utcnow().isoformat(),
        )

    def update_habit(
        self,
        habit_id,
        name,
        frequency,
        time_of_day,
        reminder,
        notes,
        goal_name,
        subgoal_name,
    ):
        name = (name or "").strip()
        frequency = (frequency or "Daily").strip()
        time_of_day = (time_of_day or "").strip() or None
        reminder = (reminder or "").strip() or None
        notes = (notes or "").strip() or None
        goal_name = (goal_name or "").strip() or None
        subgoal_name = (subgoal_name or "").strip() or None
        if not name:
            return
        self.repository.update_habit(
            int(habit_id),
            name,
            frequency,
            time_of_day,
            reminder,
            notes,
            goal_name,
            subgoal_name,
        )

    def delete_habit(self, habit_id):
        self.repository.delete_habit(int(habit_id))

    def set_habit_done(self, habit_id, log_date, done):
        self.repository.set_habit_log(int(habit_id), log_date, done)
