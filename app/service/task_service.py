import calendar
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

#test
class TaskService:
    DEMO_SEED_LOCK_ID = 922337203685477500
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

    def _get_timezone(self):
        tz_name = self.repository.get_setting("timezone") or "UTC"
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo("UTC")
            tz_name = "UTC"
        return tz_name, tz

    def _parse_bool_setting(self, value, default=False):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _parse_date(self, value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None

    def _parse_time(self, value):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%H:%M").time()
        except ValueError:
            return None

    def _parse_datetime(self, value):
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)

    def _format_occurrence_label(self, dt, now):
        if not dt:
            return "Not scheduled"
        date_value = dt.date()
        if date_value == now.date():
            return f"Today · {dt.strftime('%H:%M')}"
        if date_value == (now.date() + timedelta(days=1)):
            return f"Tomorrow · {dt.strftime('%H:%M')}"
        return dt.strftime("%a %d %b · %H:%M")

    def _weekday_label(self, index):
        labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        return labels[index % 7]

    def _next_month_date(self, base_date, target_day):
        month = base_date.month + 1
        year = base_date.year
        if month > 12:
            month = 1
            year += 1
        last_day = calendar.monthrange(year, month)[1]
        return base_date.replace(year=year, month=month, day=min(target_day, last_day))

    def _compute_next_occurrence(self, reminder, now, tz):
        if not reminder.get("is_active"):
            return None, "paused"
        interval = (reminder.get("repeat_interval") or "none").lower()
        remind_date = self._parse_date(reminder.get("remind_date"))
        remind_time = self._parse_time(reminder.get("remind_time"))
        if not remind_time:
            return None, "unscheduled"

        if interval == "none":
            if not remind_date:
                return None, "unscheduled"
            candidate = datetime.combine(remind_date, remind_time, tzinfo=tz)
            if candidate < now:
                return candidate, "overdue"
            return candidate, "upcoming"

        if interval == "daily":
            base_date = remind_date if remind_date and remind_date > now.date() else now.date()
            candidate = datetime.combine(base_date, remind_time, tzinfo=tz)
            if candidate < now:
                candidate = datetime.combine(base_date + timedelta(days=1), remind_time, tzinfo=tz)
            return candidate, "upcoming"

        if interval == "weekly":
            repeat_days = reminder.get("repeat_days") or ""
            day_indices = [
                int(day) for day in repeat_days.split(",") if day.strip().isdigit()
            ]
            if not day_indices:
                day_indices = [remind_date.weekday()] if remind_date else [now.weekday()]
            start_date = remind_date if remind_date and remind_date > now.date() else now.date()
            for offset in range(0, 14):
                candidate_date = start_date + timedelta(days=offset)
                if candidate_date.weekday() not in day_indices:
                    continue
                candidate = datetime.combine(candidate_date, remind_time, tzinfo=tz)
                if candidate >= now:
                    return candidate, "upcoming"
            return None, "unscheduled"

        if interval == "monthly":
            base_date = remind_date if remind_date and remind_date > now.date() else now.date()
            target_day = (remind_date.day if remind_date else now.day)
            last_day = calendar.monthrange(base_date.year, base_date.month)[1]
            candidate_date = base_date.replace(day=min(target_day, last_day))
            candidate = datetime.combine(candidate_date, remind_time, tzinfo=tz)
            if candidate < now:
                next_date = self._next_month_date(base_date, target_day)
                candidate = datetime.combine(next_date, remind_time, tzinfo=tz)
            return candidate, "upcoming"

        return None, "unscheduled"

    def get_notification_settings(self):
        enabled = self._parse_bool_setting(
            self.repository.get_setting("notifications_enabled"), False
        )
        interval_raw = self.repository.get_setting("notifications_interval_minutes")
        try:
            interval_minutes = int(interval_raw)
        except (TypeError, ValueError):
            interval_minutes = 30
        interval_minutes = max(1, min(interval_minutes, 240))
        show_system = self._parse_bool_setting(
            self.repository.get_setting("notifications_show_system"), True
        )
        show_toast = self._parse_bool_setting(
            self.repository.get_setting("notifications_show_toast"), True
        )
        play_sound = self._parse_bool_setting(
            self.repository.get_setting("notifications_play_sound"), True
        )
        title = self.repository.get_setting("notifications_title") or "Tracking reminder"
        message = (
            self.repository.get_setting("notifications_message")
            or "Start a Pomodoro to keep tracking your focus."
        )
        return {
            "enabled": enabled,
            "interval_minutes": interval_minutes,
            "show_system": show_system,
            "show_toast": show_toast,
            "play_sound": play_sound,
            "title": title,
            "message": message,
        }

    def set_notification_settings(self, form_data):
        enabled = self._parse_bool_setting(form_data.get("notifications_enabled"), False)
        interval_raw = form_data.get("notifications_interval_minutes", "")
        try:
            interval_minutes = int(interval_raw)
        except (TypeError, ValueError):
            interval_minutes = 30
        interval_minutes = max(1, min(interval_minutes, 240))
        show_system = self._parse_bool_setting(
            form_data.get("notifications_show_system"), True
        )
        show_toast = self._parse_bool_setting(
            form_data.get("notifications_show_toast"), True
        )
        play_sound = self._parse_bool_setting(
            form_data.get("notifications_play_sound"), True
        )
        title = (form_data.get("notifications_title") or "").strip() or "Tracking reminder"
        message = (form_data.get("notifications_message") or "").strip()
        if not message:
            message = "Start a Pomodoro to keep tracking your focus."
        self.repository.set_setting(
            "notifications_enabled", "1" if enabled else "0"
        )
        self.repository.set_setting(
            "notifications_interval_minutes", str(interval_minutes)
        )
        self.repository.set_setting(
            "notifications_show_system", "1" if show_system else "0"
        )
        self.repository.set_setting(
            "notifications_show_toast", "1" if show_toast else "0"
        )
        self.repository.set_setting(
            "notifications_play_sound", "1" if play_sound else "0"
        )
        self.repository.set_setting("notifications_title", title)
        self.repository.set_setting("notifications_message", message)

    def get_timezone_name(self):
        return self._get_timezone()[0]

    def set_timezone_name(self, tz_name):
        tz_name = (tz_name or "").strip() or "UTC"
        try:
            ZoneInfo(tz_name)
        except Exception:
            tz_name = "UTC"
        self.repository.set_setting("timezone", tz_name)

    # ----------------------
    # Profile settings
    # ----------------------
    def get_profile(self):
        return {
            "full_name": self.repository.get_setting("profile_full_name") or "",
            "phone": self.repository.get_setting("profile_phone") or "",
            "bio": self.repository.get_setting("profile_bio") or "",
            "user_id": getattr(self.repository, "user_id", None),
        }

    def update_profile(self, form_data):
        full_name = (form_data.get("full_name") or "").strip()
        phone = (form_data.get("phone") or "").strip()
        bio = (form_data.get("bio") or "").strip()
        self.repository.set_setting("profile_full_name", full_name)
        self.repository.set_setting("profile_phone", phone)
        self.repository.set_setting("profile_bio", bio)

    def current_local_date(self):
        _, tz = self._get_timezone()
        return datetime.now(tz).date()

    def list_reminders(self):
        tz_name, tz = self._get_timezone()
        now = datetime.now(tz)
        reminders = self.repository.fetch_reminders()
        reminder_list = []
        for reminder in reminders:
            reminder_dict = dict(reminder)
            next_dt, status = self._compute_next_occurrence(reminder_dict, now, tz)
            repeat_interval = (reminder_dict.get("repeat_interval") or "none").lower()
            repeat_days = reminder_dict.get("repeat_days") or ""
            day_indices = [
                int(day) for day in repeat_days.split(",") if day.strip().isdigit()
            ]
            repeat_label = "One-time"
            if repeat_interval == "daily":
                repeat_label = "Daily"
            elif repeat_interval == "weekly":
                if day_indices:
                    days_label = ", ".join(self._weekday_label(day) for day in day_indices)
                    repeat_label = f"Weekly · {days_label}"
                else:
                    repeat_label = "Weekly"
            elif repeat_interval == "monthly":
                repeat_label = "Monthly"
            channels = []
            if reminder_dict.get("channel_toast"):
                channels.append("In-app")
            if reminder_dict.get("channel_system"):
                channels.append("System")
            if reminder_dict.get("play_sound"):
                channels.append("Sound")
            reminder_list.append(
                {
                    **reminder_dict,
                    "next_at": next_dt,
                    "next_label": self._format_occurrence_label(next_dt, now),
                    "status": status,
                    "repeat_label": repeat_label,
                    "repeat_days_list": day_indices,
                    "channels_label": " · ".join(channels) if channels else "No alerts",
                    "timezone_name": tz_name,
                }
            )
        return reminder_list

    def reminders_summary(self, reminders):
        tz_name, tz = self._get_timezone()
        now = datetime.now(tz)
        active = [reminder for reminder in reminders if reminder.get("is_active")]
        overdue = [reminder for reminder in reminders if reminder.get("status") == "overdue"]
        next_candidates = [
            reminder.get("next_at")
            for reminder in active
            if reminder.get("next_at")
        ]
        next_up = min(next_candidates) if next_candidates else None
        return {
            "total": len(reminders),
            "active": len(active),
            "overdue": len(overdue),
            "next_label": self._format_occurrence_label(next_up, now),
        }

    def add_reminder(self, form_data):
        title = (form_data.get("title") or "").strip()
        if not title:
            return
        notes = (form_data.get("notes") or "").strip() or None
        remind_date = (form_data.get("remind_date") or "").strip() or None
        remind_time = (form_data.get("remind_time") or "").strip() or None
        repeat_interval = (form_data.get("repeat_interval") or "none").strip().lower()
        repeat_days = form_data.getlist("repeat_days")
        repeat_days_clean = ",".join(
            str(int(day)) for day in repeat_days if str(day).isdigit()
        )
        priority = (form_data.get("priority") or "normal").strip().lower()
        channel_toast = self._parse_bool_setting(form_data.get("channel_toast"), False)
        channel_system = self._parse_bool_setting(form_data.get("channel_system"), False)
        play_sound = self._parse_bool_setting(form_data.get("play_sound"), False)
        is_active = self._parse_bool_setting(form_data.get("is_active"), False)
        self.repository.create_reminder(
            title,
            notes,
            remind_date,
            remind_time,
            repeat_interval,
            repeat_days_clean or None,
            priority,
            1 if channel_toast else 0,
            1 if channel_system else 0,
            1 if play_sound else 0,
            1 if is_active else 0,
            datetime.utcnow().isoformat(),
        )

    def update_reminder(self, reminder_id, form_data):
        title = (form_data.get("title") or "").strip()
        if not title:
            return
        notes = (form_data.get("notes") or "").strip() or None
        remind_date = (form_data.get("remind_date") or "").strip() or None
        remind_time = (form_data.get("remind_time") or "").strip() or None
        repeat_interval = (form_data.get("repeat_interval") or "none").strip().lower()
        repeat_days = form_data.getlist("repeat_days")
        repeat_days_clean = ",".join(
            str(int(day)) for day in repeat_days if str(day).isdigit()
        )
        priority = (form_data.get("priority") or "normal").strip().lower()
        channel_toast = self._parse_bool_setting(form_data.get("channel_toast"), False)
        channel_system = self._parse_bool_setting(form_data.get("channel_system"), False)
        play_sound = self._parse_bool_setting(form_data.get("play_sound"), False)
        is_active = self._parse_bool_setting(form_data.get("is_active"), False)
        self.repository.update_reminder(
            int(reminder_id),
            title,
            notes,
            remind_date,
            remind_time,
            repeat_interval,
            repeat_days_clean or None,
            priority,
            1 if channel_toast else 0,
            1 if channel_system else 0,
            1 if play_sound else 0,
            1 if is_active else 0,
        )

    def set_reminder_active(self, reminder_id, is_active):
        self.repository.set_reminder_active(int(reminder_id), bool(is_active))

    def delete_reminder(self, reminder_id):
        self.repository.delete_reminder(int(reminder_id))

    def list_todos_for_today(self):
        today = self.current_local_date().isoformat()
        todos = [dict(row) for row in self.repository.fetch_todos_for_date(today)]
        open_todos = []
        done_todos = []
        for todo in todos:
            if todo.get("completed_at"):
                done_todos.append(todo)
            else:
                open_todos.append(todo)
        return {"todos": open_todos, "done_todos": done_todos}

    def add_todo(self, name):
        name = (name or "").strip()
        if not name:
            return
        today = self.current_local_date().isoformat()
        self.repository.create_todo(name, today, datetime.utcnow().isoformat())

    def set_todo_done(self, todo_id, done):
        completed_at = datetime.utcnow().isoformat() if done else None
        self.repository.set_todo_completed(int(todo_id), completed_at)

    def delete_todo(self, todo_id):
        self.repository.delete_todo(int(todo_id))

    def _local_day_bounds(self, day):
        _, tz = self._get_timezone()
        start_local = datetime.combine(day, datetime.min.time(), tzinfo=tz)
        end_local = start_local + timedelta(days=1)
        start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
        end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
        return start_utc, end_utc

    def _rollover_running_entries(self):
        today = self.current_local_date()
        today_start, _ = self._local_day_bounds(today)
        running_entries = self.repository.fetch_running_time_entries()
        for entry in running_entries:
            started_at = self._parse_datetime(entry["started_at"])
            end_at = None
            if started_at < today_start:
                end_at = today_start
            pomodoro_end = started_at + timedelta(minutes=25)
            if datetime.utcnow() >= pomodoro_end:
                end_at = pomodoro_end if end_at is None else min(end_at, pomodoro_end)
            if end_at:
                self.repository.stop_time_entry(entry["id"], end_at.isoformat())

    def _hydrate_tasks(self, tasks, log_date):
        task_ids = [task["id"] for task in tasks]
        labels_map = self.repository.fetch_task_labels_map(task_ids)
        checked_today = self.repository.fetch_task_daily_checks_for_date(
            task_ids, log_date
        )
        check_counts = self.repository.fetch_task_daily_check_counts(task_ids)
        goals_map = self.repository.fetch_task_goals_map(task_ids)
        hydrated = []
        for task in tasks:
            task_id = task["id"]
            data = dict(task)
            status = data.get("status") or "active"
            task_goals = goals_map.get(task_id, [])
            primary_goal = task_goals[0] if task_goals else None
            hydrated.append(
                {
                    **data,
                    "status": status,
                    "labels": labels_map.get(task_id, []),
                    "checked_today": task_id in checked_today,
                    "daily_checks": int(check_counts.get(task_id, 0) or 0),
                    "goals": task_goals,
                    "goal_id": primary_goal["id"] if primary_goal else None,
                    "goal_name": primary_goal["name"] if primary_goal else None,
                }
            )
        return hydrated

    def init_db(self):
        self.repository.init_db()

    def ensure_user_setup(self, email):
        # Ensure user exists in the database first
        self.repository.ensure_user(email)
        # Then create default project
        default_project_id = self.repository.ensure_default_project(
            "General", datetime.utcnow().isoformat()
        )
        if default_project_id:
            self.repository.backfill_tasks_project(default_project_id)

    def seed_demo_from_file(self, force=False, email=None):
        if self.repository.user_id is None:
            return False, "User context not set."
        seed_email = email or "demo@goalixa.local"
        self.repository.advisory_lock(self.DEMO_SEED_LOCK_ID)
        try:
            self.repository.ensure_user(seed_email)
            if not force and self.repository.user_has_any_data():
                return False, "User already has data. Seed skipped."
            if force:
                self.repository.clear_user_data()
            root = Path(__file__).resolve().parents[2]
            template_path = root / "scripts" / "demo_seed.sql"
            if not template_path.exists():
                return False, "Seed file not found."
            sql_template = template_path.read_text(encoding="utf-8")
            rendered_sql = sql_template.replace("{{user_id}}", str(self.repository.user_id))
            self.repository.execute_sql(rendered_sql)
            return True, "Seed completed."
        finally:
            self.repository.advisory_unlock(self.DEMO_SEED_LOCK_ID)

    def list_tasks(self):
        self._rollover_running_entries()
        now_utc = datetime.utcnow()
        today = self.current_local_date()
        day_start, _ = self._local_day_bounds(today)
        log_date = today.isoformat()
        now_ts = int(now_utc.timestamp())
        day_start_ts = int(day_start.timestamp())
        rolling_start_ts = now_ts - 24 * 60 * 60
        tasks = self.repository.fetch_tasks(now_ts, rolling_start_ts, day_start_ts)
        return self._hydrate_tasks(tasks, log_date)

    def list_tasks_by_project(self, project_id):
        now_utc = datetime.utcnow()
        today = self.current_local_date()
        day_start, _ = self._local_day_bounds(today)
        log_date = today.isoformat()
        now_ts = int(now_utc.timestamp())
        day_start_ts = int(day_start.timestamp())
        rolling_start_ts = now_ts - 24 * 60 * 60
        tasks = self.repository.fetch_tasks_by_project(
            project_id,
            now_ts,
            rolling_start_ts,
            day_start_ts,
        )
        return self._hydrate_tasks(tasks, log_date)

    def list_tasks_for_today(self):
        tasks = self.list_tasks()
        active_tasks = []
        done_today_tasks = []
        completed_tasks = []
        for task in tasks:
            status = task.get("status") or "active"
            if status == "completed":
                completed_tasks.append(task)
            elif task.get("checked_today"):
                done_today_tasks.append(task)
            else:
                active_tasks.append(task)
        return {
            "tasks": active_tasks,
            "done_today_tasks": done_today_tasks,
            "completed_tasks": completed_tasks,
        }

    def add_task(self, name, project_id, label_ids=None, goal_id=None):
        name = (name or "").strip()
        if name:
            project_value = int(project_id) if project_id else None
            task_id = self.repository.create_task(
                name, datetime.utcnow().isoformat(), project_value
            )
            for label_id in label_ids or []:
                self.repository.add_label_to_task(task_id, int(label_id))
            if goal_id:
                self.repository.set_task_goal(task_id, int(goal_id))

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
                "label_ids": [
                    label["id"] for label in labels_map.get(project["id"], [])
                ],
            }
            for project in projects
        ]

    def get_project(self, project_id):
        project = self.repository.fetch_project(project_id)
        if project is None:
            return None
        labels_map = self.repository.fetch_project_labels_map([project["id"]])
        project_labels = labels_map.get(project["id"], [])
        return {
            **dict(project),
            "labels": project_labels,
            "label_ids": [label["id"] for label in project_labels],
        }

    def add_project(self, name, label_ids=None):
        name = (name or "").strip()
        if name:
            project_id = self.repository.create_project(
                name, datetime.utcnow().isoformat()
            )
            for label_id in label_ids or []:
                self.repository.add_label_to_project(project_id, int(label_id))

    def update_project(self, project_id, name, label_ids=None):
        name = (name or "").strip()
        if name:
            self.repository.update_project(int(project_id), name)
        if label_ids is not None:
            self.repository.set_project_labels(int(project_id), label_ids)

    def delete_project(self, project_id):
        self.repository.delete_project(project_id)

    def summary_by_days(self, days):
        days = int(days)
        today = self.current_local_date()
        start_date = today - timedelta(days=days - 1)
        start_day, _ = self._local_day_bounds(start_date)
        _, end_day = self._local_day_bounds(today)
        entries = self.repository.fetch_time_entries_between(
            start_day.isoformat(), end_day.isoformat()
        )

        buckets = []
        for day_offset in range(days):
            day = start_date + timedelta(days=day_offset)
            day_start, day_end = self._local_day_bounds(day)
            buckets.append(
                {
                    "date": day.isoformat(),
                    "label": day.strftime("%d %b"),
                    "start": day_start,
                    "end": day_end,
                    "seconds": 0,
                }
            )

        for entry in entries:
            entry_start = self._parse_datetime(entry["started_at"])
            entry_end = (
                self._parse_datetime(entry["ended_at"])
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
        self._rollover_running_entries()
        start_day, _ = self._local_day_bounds(start_date)
        _, end_day = self._local_day_bounds(end_date)

        entries = self.repository.fetch_time_entries_between(
            start_day.isoformat(), end_day.isoformat()
        )

        days = (end_date - start_date).days + 1
        buckets = []
        for day_offset in range(days):
            day = start_date + timedelta(days=day_offset)
            day_start, day_end = self._local_day_bounds(day)
            buckets.append(
                {
                    "date": day.isoformat(),
                    "label": day.strftime("%d %b"),
                    "start": day_start,
                    "end": day_end,
                    "seconds": 0,
                }
            )

        for entry in entries:
            entry_start = self._parse_datetime(entry["started_at"])
            entry_end = (
                self._parse_datetime(entry["ended_at"])
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
        self._rollover_running_entries()
        start_day, _ = self._local_day_bounds(start_date)
        _, end_day = self._local_day_bounds(end_date)
        entries = self.repository.fetch_time_entries_with_projects_between(
            start_day.isoformat(), end_day.isoformat()
        )

        totals = {}
        for entry in entries:
            entry_start = self._parse_datetime(entry["started_at"])
            entry_end = (
                self._parse_datetime(entry["ended_at"])
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
        self._rollover_running_entries()
        start_day, _ = self._local_day_bounds(start_date)
        _, end_day = self._local_day_bounds(end_date)

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
            entry_start = self._parse_datetime(entry["started_at"])
            entry_end = (
                self._parse_datetime(entry["ended_at"])
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

    def project_totals_by_range(self, start_date, end_date):
        self._rollover_running_entries()
        start_day, _ = self._local_day_bounds(start_date)
        _, end_day = self._local_day_bounds(end_date)
        entries = self.repository.fetch_time_entries_with_task_details_between(
            start_day.isoformat(), end_day.isoformat()
        )
        if not entries:
            return []

        task_ids = {entry["task_id"] for entry in entries}
        task_id_list = list(task_ids)
        labels_map = self.repository.fetch_task_labels_map(task_id_list)
        running_map = {
            task_id: self.repository.is_task_running(task_id)
            for task_id in task_id_list
        }

        projects = {}
        now = datetime.utcnow()
        for entry in entries:
            entry_start = self._parse_datetime(entry["started_at"])
            entry_end = (
                self._parse_datetime(entry["ended_at"])
                if entry["ended_at"]
                else now
            )
            overlap_start = max(entry_start, start_day)
            overlap_end = min(entry_end, end_day)
            if overlap_end <= overlap_start:
                continue

            seconds = int((overlap_end - overlap_start).total_seconds())
            project_name = entry["project_name"] or "Unassigned"
            project = projects.setdefault(
                project_name,
                {"name": project_name, "total_seconds": 0, "tasks": {}},
            )
            project["total_seconds"] += seconds

            task_id = entry["task_id"]
            task = project["tasks"].setdefault(
                task_id,
                {
                    "id": task_id,
                    "name": entry["task_name"] or "Unnamed Task",
                    "total_seconds": 0,
                    "labels": labels_map.get(task_id, []),
                    "is_running": bool(running_map.get(task_id, False)),
                },
            )
            task["total_seconds"] += seconds

        project_list = []
        for project in projects.values():
            tasks = list(project["tasks"].values())
            tasks.sort(key=lambda item: item["total_seconds"], reverse=True)
            project_list.append(
                {
                    "name": project["name"],
                    "total_seconds": project["total_seconds"],
                    "tasks": tasks,
                }
            )
        project_list.sort(key=lambda item: item["total_seconds"], reverse=True)
        return project_list

    def report_entities_by_range(self, start_date, end_date):
        start_day, _ = self._local_day_bounds(start_date)
        _, end_day = self._local_day_bounds(end_date)
        start_iso = start_day.isoformat()
        end_iso = end_day.isoformat()

        goals_created = self.repository.fetch_goals_created_count(start_iso, end_iso)
        goal_status_counts = self.repository.fetch_goal_status_counts(start_iso, end_iso)
        goals_due = self.repository.fetch_goal_due_count(
            start_date.isoformat(), end_date.isoformat()
        )

        habits_created = self.repository.fetch_habits_created_count(start_iso, end_iso)
        total_habits = self.repository.fetch_total_habits_count()
        habit_logs = self.repository.fetch_habit_log_stats(
            start_date.isoformat(), end_date.isoformat()
        )

        projects_created = self.repository.fetch_projects_created_count(start_iso, end_iso)
        project_totals = self.project_totals_by_range(start_date, end_date)
        active_projects = len(project_totals)

        tasks_created = self.repository.fetch_tasks_created_count(start_iso, end_iso)
        tasks_completed = self.repository.fetch_tasks_completed_count(start_iso, end_iso)
        active_task_ids = {
            task["id"]
            for project in project_totals
            for task in project.get("tasks", [])
        }

        days = max((end_date - start_date).days + 1, 1)
        habit_avg_per_day = habit_logs["total_logs"] / days

        return {
            "goals": {
                "created": goals_created,
                "active": int(goal_status_counts.get("active", 0))
                + int(goal_status_counts.get("at_risk", 0)),
                "completed": int(goal_status_counts.get("completed", 0)),
                "due": goals_due,
            },
            "habits": {
                "created": habits_created,
                "total": total_habits,
                "active": habit_logs["active_habits"],
                "logs": habit_logs["total_logs"],
                "active_days": habit_logs["active_days"],
                "avg_per_day": habit_avg_per_day,
            },
            "projects": {
                "created": projects_created,
                "active": active_projects,
            },
            "tasks": {
                "created": tasks_created,
                "completed": tasks_completed,
                "active": len(active_task_ids),
            },
        }

    def list_time_entries_by_range(self, start_date, end_date):
        self._rollover_running_entries()
        start_day, _ = self._local_day_bounds(start_date)
        _, end_day = self._local_day_bounds(end_date)
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
        today = self.current_local_date()
        for day_offset in range(days):
            day = start_date + timedelta(days=day_offset)
            day_start, day_end = self._local_day_bounds(day)
            if day == today:
                label = "Today"
            elif day == (today - timedelta(days=1)):
                label = "Yesterday"
            else:
                label = day.strftime("%a, %d %b")
            buckets.append(
                {
                    "label": label,
                    "start": day_start,
                    "end": day_end,
                    "tasks": {},
                    "total_seconds": 0,
                }
            )

        now = datetime.utcnow()
        for entry in entries:
            entry_start = self._parse_datetime(entry["started_at"])
            entry_end = (
                self._parse_datetime(entry["ended_at"])
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
                task = bucket["tasks"].get(entry["task_id"])
                if not task:
                    task = {
                        "task_id": entry["task_id"],
                        "task_name": entry["task_name"] or "Unnamed Task",
                        "project_name": entry["project_name"] or "Unassigned",
                        "labels": entry_labels,
                        "total_seconds": 0,
                        "entries": [],
                        "is_running": bool(running_map.get(entry["task_id"], False)),
                        "sort_ts": overlap_start.timestamp(),
                    }
                    bucket["tasks"][entry["task_id"]] = task
                task["total_seconds"] += duration
                task["sort_ts"] = max(task["sort_ts"], overlap_start.timestamp())
                task["entries"].append(
                    {
                        "duration_seconds": duration,
                        "start_time": self._format_time(overlap_start),
                        "end_time": self._format_time(overlap_end),
                        "sort_ts": overlap_start.timestamp(),
                    }
                )

        result = []
        for bucket in buckets:
            if not bucket["tasks"]:
                continue
            tasks = list(bucket["tasks"].values())
            for task in tasks:
                task["entries"].sort(key=lambda item: item["sort_ts"], reverse=True)
                for entry in task["entries"]:
                    entry.pop("sort_ts", None)
            tasks.sort(key=lambda item: item["sort_ts"], reverse=True)
            for task in tasks:
                task.pop("sort_ts", None)
            bucket["tasks"] = tasks
            bucket.pop("start", None)
            bucket.pop("end", None)
            result.append(bucket)

        return result

    def _sum_time_entries_between(self, start_date, end_date):
        start_day, _ = self._local_day_bounds(start_date)
        _, end_day = self._local_day_bounds(end_date)
        entries = self.repository.fetch_time_entries_with_task_details_between(
            start_day.isoformat(), end_day.isoformat()
        )
        now = datetime.utcnow()
        total_seconds = 0
        for entry in entries:
            entry_start = self._parse_datetime(entry["started_at"])
            entry_end = (
                self._parse_datetime(entry["ended_at"])
                if entry["ended_at"]
                else now
            )
            overlap_start = max(entry_start, start_day)
            overlap_end = min(entry_end, end_day)
            if overlap_end <= overlap_start:
                continue
            total_seconds += int((overlap_end - overlap_start).total_seconds())
        return total_seconds

    def current_week_range(self):
        today = self.current_local_date()
        tz_name, _ = self._get_timezone()
        if tz_name == "Asia/Tehran":
            start_offset = (today.weekday() + 2) % 7
        else:
            start_offset = today.weekday()
        start_date = today - timedelta(days=start_offset)
        end_date = start_date + timedelta(days=6)
        return start_date, end_date

    def list_weekly_goals(self, week_start=None, week_end=None):
        goals = self.repository.fetch_weekly_goals(
            week_start=week_start, week_end=week_end
        )
        if not goals:
            return []
        totals_map = {}
        goal_list = []
        for goal in goals:
            try:
                start_date = datetime.fromisoformat(goal["week_start"]).date()
                end_date = datetime.fromisoformat(goal["week_end"]).date()
            except ValueError:
                continue
            key = (start_date, end_date)
            if key not in totals_map:
                totals_map[key] = self._sum_time_entries_between(start_date, end_date)
            total_seconds = totals_map[key]
            target_seconds = int(goal["target_seconds"] or 0)
            progress = int((total_seconds / target_seconds) * 100) if target_seconds else 0
            progress = min(progress, 100)
            week_label = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"
            goal_list.append(
                {
                    **dict(goal),
                    "progress_seconds": total_seconds,
                    "progress_percent": progress,
                    "week_label": week_label,
                }
            )
        return goal_list

    def add_weekly_goal(self, title, target_hours, week_start, week_end):
        title = (title or "").strip()
        if not title:
            return
        target_seconds = int(float(target_hours or 0) * 3600)
        created_at = datetime.utcnow().isoformat()
        self.repository.create_weekly_goal(
            title,
            target_seconds,
            week_start,
            week_end,
            "active",
            created_at,
        )

    def update_weekly_goal(self, goal_id, title, target_hours, status):
        title = (title or "").strip()
        status = (status or "active").strip()
        target_seconds = int(float(target_hours or 0) * 3600)
        if not title:
            return
        self.repository.update_weekly_goal(goal_id, title, target_seconds, status)

    def toggle_weekly_goal_status(self, goal_id, status):
        status = (status or "active").strip()
        current = self.repository.fetch_weekly_goals()
        match = next((item for item in current if item["id"] == int(goal_id)), None)
        if not match:
            return
        self.repository.update_weekly_goal(
            goal_id, match["title"], match["target_seconds"], status
        )

    def delete_weekly_goal(self, goal_id):
        self.repository.delete_weekly_goal(goal_id)

    def list_time_entries_for_calendar(self, start_dt, end_dt):
        self._rollover_running_entries()
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
            entry_start = self._parse_datetime(entry["started_at"])
            entry_end = (
                self._parse_datetime(entry["ended_at"])
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

        subgoal_project_ids = sorted(
            {
                subgoal["project_id"]
                for subgoals in goal_subgoals_map.values()
                for subgoal in subgoals
                if subgoal.get("project_id")
            }
        )
        subgoal_projects = self.repository.fetch_projects_by_ids(subgoal_project_ids)
        subgoal_projects_by_id = {
            project["id"]: dict(project) for project in subgoal_projects
        }

        goal_list = []
        today = self.current_local_date()
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
            deadline_total_days = None
            deadline_remaining_days = None
            deadline_percent = None
            target_date_value = goal["target_date"] if "target_date" in goal.keys() else None
            if target_date_value:
                try:
                    target_date = datetime.fromisoformat(target_date_value).date()
                except ValueError:
                    target_date = None
                if target_date:
                    try:
                        created_date = datetime.fromisoformat(goal["created_at"]).date()
                    except ValueError:
                        created_date = today
                    total_days = max(1, (target_date - created_date).days)
                    remaining_days = max(0, (target_date - today).days)
                    deadline_total_days = total_days
                    deadline_remaining_days = remaining_days
                    deadline_percent = min(100, max(0, int((remaining_days / total_days) * 100)))
            subgoals = []
            for subgoal in goal_subgoals_map.get(goal_id, []):
                project_id = subgoal.get("project_id")
                project = (
                    subgoal_projects_by_id.get(project_id) if project_id else None
                )
                subgoals.append(
                    {
                        **subgoal,
                        "project_name": project["name"] if project else None,
                    }
                )
            subgoals_total = len(subgoals)
            subgoals_done = sum(1 for subgoal in subgoals if subgoal["status"] == "completed")
            if subgoals_total:
                progress = int((subgoals_done / subgoals_total) * 100)
                display_status = "completed" if subgoals_done == subgoals_total else "active"
            else:
                target_seconds = int(goal["target_seconds"] or 0)
                progress = int((total_seconds / target_seconds) * 100) if target_seconds else 0
                progress = min(progress, 100)
                display_status = goal["status"]

            goal_list.append(
                {
                    **dict(goal),
                    "project_ids": linked_project_ids,
                    "task_ids": direct_task_ids,
                    "projects": [projects_by_id[pid] for pid in linked_project_ids if pid in projects_by_id],
                    "subgoals": subgoals,
                    "subgoals_count": subgoals_total,
                    "subgoals_completed": subgoals_done,
                    "total_seconds": total_seconds,
                    "progress": progress,
                    "display_status": display_status,
                    "tasks_count": len(linked_task_ids),
                    "projects_count": len(linked_project_ids),
                    "deadline_total_days": deadline_total_days,
                    "deadline_remaining_days": deadline_remaining_days,
                    "deadline_percent": deadline_percent,
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
        if subgoals_text is not None:
            subgoals = self._parse_subgoals(subgoals_text)
            self.repository.set_goal_subgoals(
                int(goal_id), subgoals, datetime.utcnow().isoformat()
            )

    def delete_goal(self, goal_id):
        self.repository.delete_goal(goal_id)

    def set_goal_subgoal_status(self, subgoal_id, done):
        subgoal = self.repository.fetch_goal_subgoal(int(subgoal_id))
        if not subgoal:
            return
        status = "completed" if done else "pending"
        self.repository.set_goal_subgoal_status(int(subgoal_id), status)
        goal_id = subgoal["goal_id"]
        subgoals = self.repository.fetch_goal_subgoals([goal_id]).get(goal_id, [])
        if not subgoals:
            return
        completed = sum(1 for item in subgoals if item["status"] == "completed")
        goal_status = "completed" if completed == len(subgoals) else "active"
        goal = self.repository.fetch_goal(goal_id)
        if not goal:
            return
        self.repository.update_goal(
            int(goal_id),
            goal["name"],
            goal["description"],
            goal_status,
            goal["priority"],
            goal["target_date"],
            int(goal["target_seconds"] or 0),
        )

    def add_goal_subgoal(self, goal_id, title, label, target_date, project_id):
        title = (title or "").strip()
        if not title:
            return
        label = (label or "").strip() or None
        target_date = (target_date or "").strip() or None
        project_id = int(project_id) if str(project_id).strip() else None
        self.repository.add_goal_subgoal(
            int(goal_id),
            title,
            label,
            target_date,
            project_id,
            datetime.utcnow().isoformat(),
        )

    def start_task(self, task_id):
        if not self.repository.is_task_running(task_id):
            self.repository.start_task(task_id, datetime.utcnow().isoformat())

    def stop_task(self, task_id):
        self.repository.stop_task(task_id, datetime.utcnow().isoformat())

    def delete_task(self, task_id):
        self.repository.delete_task(task_id)

    def set_task_daily_check(self, task_id, done):
        log_date = self.current_local_date().isoformat()
        self.repository.set_task_daily_check(int(task_id), log_date, done)

    def list_task_daily_checks(self, task_ids, start_date, end_date):
        if not task_ids:
            return {}
        start_iso = start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date)
        end_iso = end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date)
        return self.repository.fetch_task_daily_checks_between(task_ids, start_iso, end_iso)

    def list_habit_logs_between(self, habit_ids, start_date, end_date):
        if not habit_ids:
            return {}
        start_iso = start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date)
        end_iso = end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date)
        return self.repository.fetch_habit_logs_between(habit_ids, start_iso, end_iso)

    def set_task_status(self, task_id, status):
        status = (status or "").strip().lower()
        if status not in {"active", "completed"}:
            return
        completed_at = datetime.utcnow().isoformat() if status == "completed" else None
        if status == "completed" and self.repository.is_task_running(task_id):
            self.repository.stop_task(task_id, datetime.utcnow().isoformat())
        self.repository.set_task_status(int(task_id), status, completed_at)

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
        today = self.current_local_date()
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
