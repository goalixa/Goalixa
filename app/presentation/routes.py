from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import jsonify, request
from werkzeug.datastructures import MultiDict

from app.auth_client import auth_required, current_user


def register_routes(app, service):
    BULK_TASK_ACTIONS = {
        "start",
        "stop",
        "delete",
        "daily-check",
        "complete",
        "reopen",
    }

    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint for Kubernetes probes (no auth required)."""
        return jsonify({"status": "ok"}), 200

    @app.before_request
    def load_user_context():
        if current_user.is_authenticated:
            service.repository.set_user_id(current_user.id)
            service.ensure_user_setup(current_user.email)
            return
        service.repository.set_user_id(None)

    @app.before_request
    def auto_complete_overdue_timers():
        # Keep timer state consistent even when a user returns after token/session gaps.
        if request.path == "/health":
            return
        if not current_user.is_authenticated:
            return
        try:
            service.complete_overdue_timers(max_duration_seconds=1500)
        except Exception:
            pass

    def parse_iso(value):
        if not value:
            return None
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None

        tz_name = service.get_timezone_name()
        tz = timezone.utc
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = timezone.utc

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=tz)
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)

    def build_week_days(week_start, today):
        week_dates = [week_start + timedelta(days=offset) for offset in range(7)]
        week_days = []
        for day_value in week_dates:
            week_days.append(
                {
                    "iso": day_value.isoformat(),
                    "day": day_value.strftime("%a"),
                    "date": day_value.strftime("%d"),
                    "full": day_value.strftime("%b %d"),
                    "is_today": day_value == today,
                    "is_future": day_value > today,
                }
            )
        return week_days

    def _json_payload():
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            return payload
        return {}

    def _to_multi_dict(payload):
        form_data = MultiDict()
        if not isinstance(payload, dict):
            return form_data

        for key, value in payload.items():
            if isinstance(value, list):
                form_data.setlist(
                    key,
                    [
                        "" if item is None else str(item)
                        for item in value
                        if item is not None
                    ],
                )
            elif value is not None:
                form_data.add(key, str(value))
        return form_data

    def _coerce_list(value):
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return [item for item in value if str(item).strip()]
        if str(value).strip():
            return [value]
        return []

    def _coerce_bool(value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        return str(value).strip().lower() in {"1", "true", "on", "yes"}

    def _parse_task_ids(values):
        if values is None:
            return []
        if isinstance(values, str):
            raw_values = [value.strip() for value in values.split(",")]
        elif isinstance(values, (list, tuple, set)):
            raw_values = values
        else:
            raw_values = [values]

        task_ids = []
        seen = set()
        for raw_value in raw_values:
            try:
                task_id = int(raw_value)
            except (TypeError, ValueError):
                continue
            if task_id <= 0 or task_id in seen:
                continue
            seen.add(task_id)
            task_ids.append(task_id)
        return task_ids

    def _run_task_action(task_id, action):
        if action == "start":
            service.start_task(task_id)
            return
        if action == "stop":
            service.stop_task(task_id)
            return
        if action == "delete":
            service.delete_task(task_id)
            return
        if action == "daily-check":
            service.set_task_daily_check(task_id, True)
            return
        if action == "complete":
            service.set_task_status(task_id, "completed")
            return
        if action == "reopen":
            service.set_task_status(task_id, "active")

    def _run_bulk_task_action(task_ids, action):
        normalized_action = (action or "").strip().lower()
        if normalized_action not in BULK_TASK_ACTIONS:
            return False
        for task_id in task_ids:
            _run_task_action(task_id, normalized_action)
        return True

    def _serialize_task(task):
        return {
            "id": task["id"],
            "name": task["name"],
            "total_seconds": int(task["total_seconds"] or 0),
            "rolling_24h_seconds": int(task["rolling_24h_seconds"] or 0),
            "today_seconds": int(task.get("today_seconds") or 0),
            "is_running": bool(task["is_running"]),
            "project_id": task["project_id"],
            "project_name": task["project_name"],
            "labels": task["labels"],
            "goal_id": task.get("goal_id"),
            "goal_name": task.get("goal_name"),
            "goals": task.get("goals", []),
            "status": task.get("status") or "active",
            "checked_today": bool(task.get("checked_today")),
            "daily_checks": int(task.get("daily_checks") or 0),
            "completed_at": task.get("completed_at"),
            "priority": task.get("priority") or "medium",
        }

    def _build_tasks_payload():
        task_view = service.list_tasks_for_today()
        return {
            "tasks": [_serialize_task(task) for task in task_view["tasks"]],
            "done_today_tasks": [
                _serialize_task(task) for task in task_view["done_today_tasks"]
            ],
            "completed_tasks": [
                _serialize_task(task) for task in task_view["completed_tasks"]
            ],
        }

    def _build_timer_dashboard_payload():
        start = request.args.get("start")
        end = request.args.get("end")
        if start and end:
            try:
                start_date = datetime.fromisoformat(start).date()
                end_date = datetime.fromisoformat(end).date()
            except ValueError:
                end_date = service.current_local_date()
                start_date = end_date - timedelta(days=6)
        else:
            end_date = service.current_local_date()
            start_date = end_date - timedelta(days=6)

        if end_date < start_date:
            start_date, end_date = end_date, start_date

        timer_list_groups = service.list_time_entries_by_range(start_date, end_date)

        today = service.current_local_date()
        today_target_seconds = service.get_daily_target(today)
        today_total_seconds = 0
        for group in timer_list_groups:
            if group["label"] == "Today":
                today_total_seconds = group["total_seconds"]
                break

        week_start, week_end = service.current_week_range()
        week_total_seconds = 0
        week_groups = service.list_time_entries_by_range(week_start, week_end)
        for group in week_groups:
            week_total_seconds += group["total_seconds"]

        tasks = [
            task
            for task in service.list_tasks()
            if (task.get("status") or "active") != "completed"
        ]
        week_days = build_week_days(week_start, today)
        task_ids = [task["id"] for task in tasks]
        checks_map = service.list_task_daily_checks(task_ids, week_start, week_end)
        task_rows = []
        for task in tasks:
            checked_dates = checks_map.get(task["id"], set())
            week_checks = [day["iso"] in checked_dates for day in week_days]
            task_rows.append({**task, "week_checks": week_checks})

        return {
            "timer_list_groups": timer_list_groups,
            "timer_range_start": start_date.isoformat(),
            "timer_range_end": end_date.isoformat(),
            "today_total_seconds": today_total_seconds,
            "today_target_seconds": today_target_seconds,
            "week_total_seconds": week_total_seconds,
            "week_label": f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
            "week_days": week_days,
            "task_rows": task_rows,
            "today_date": today.isoformat(),
            "projects": service.list_projects(),
            "labels": service.list_labels(),
        }

    def _build_planner_payload():
        today = service.current_local_date().isoformat()
        habits_list = service.list_habits(today)
        habits_summary = service.habits_summary(habits_list)
        todo_view = service.list_todos_for_today()
        return {
            "today": today,
            "habits": habits_list,
            "habits_summary": habits_summary,
            "todos": todo_view["todos"],
            "done_todos": todo_view["done_todos"],
        }

    def _build_habits_payload():
        today = service.current_local_date().isoformat()
        habits_list = service.list_habits(today)
        summary = service.habits_summary(habits_list)
        goals_list = service.list_goals()
        series = service.habit_completion_series(14)
        return {
            "today": today,
            "habits": habits_list,
            "goals": goals_list,
            "total_habits": summary["total"],
            "completed_habits": summary["completed"],
            "best_streak": summary["best_streak"],
            "focus_window": summary["focus_window"],
            "habit_series": series,
        }

    def _build_goals_payload():
        goals_list = service.list_goals()
        active_goals = [
            goal for goal in goals_list if goal.get("status") in {"active", "at_risk"}
        ]
        total_goal_seconds = sum(goal.get("total_seconds", 0) for goal in goals_list)
        targets_set = len([goal for goal in goals_list if goal.get("target_date")])
        week_start, week_end = service.current_week_range()
        weekly_goals = service.list_weekly_goals(
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
        )
        return {
            "goals": goals_list,
            "active_goals_count": len(active_goals),
            "total_goal_seconds": total_goal_seconds,
            "targets_set": targets_set,
            "weekly_goals": weekly_goals,
            "weekly_range_label": f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
            "projects": service.list_projects(),
            "tasks": service.list_tasks(),
            "labels": service.list_labels(),
        }

    def _build_weekly_goals_payload():
        week_start_arg = request.args.get("week_start")
        week_end_arg = request.args.get("week_end")
        if week_start_arg and week_end_arg:
            week_start = week_start_arg
            week_end = week_end_arg
            try:
                week_start_date = datetime.fromisoformat(week_start_arg).date()
                week_end_date = datetime.fromisoformat(week_end_arg).date()
            except ValueError:
                week_start_date, week_end_date = service.current_week_range()
                week_start = week_start_date.isoformat()
                week_end = week_end_date.isoformat()
        else:
            week_start_date, week_end_date = service.current_week_range()
            week_start = week_start_date.isoformat()
            week_end = week_end_date.isoformat()

        weekly_current = service.list_weekly_goals(
            week_start=week_start,
            week_end=week_end,
        )
        weekly_all = service.list_weekly_goals()
        return {
            "weekly_goals_current": weekly_current,
            "weekly_goals_all": weekly_all,
            "weekly_range_label": f"{week_start_date.strftime('%b %d')} - {week_end_date.strftime('%b %d')}",
            "week_start": week_start,
            "week_end": week_end,
            "long_term_goals": service.list_goals(),
            "labels": service.list_labels(),
        }

    def _build_reminders_payload():
        reminders_list = service.list_reminders()
        summary = service.reminders_summary(reminders_list)
        today = service.current_local_date().isoformat()
        notification_settings = service.get_notification_settings()
        weekday_options = [
            {"value": 0, "label": "Mon"},
            {"value": 1, "label": "Tue"},
            {"value": 2, "label": "Wed"},
            {"value": 3, "label": "Thu"},
            {"value": 4, "label": "Fri"},
            {"value": 5, "label": "Sat"},
            {"value": 6, "label": "Sun"},
        ]
        return {
            "reminders": reminders_list,
            "reminders_summary": summary,
            "notification_settings": notification_settings,
            "today": today,
            "weekday_options": weekday_options,
        }

    def _build_labels_payload():
        return {"labels": service.list_labels()}

    def _timezone_options():
        return [
            "UTC",
            "Asia/Tehran",
            "Europe/London",
            "Europe/Berlin",
            "America/New_York",
            "America/Chicago",
            "America/Los_Angeles",
            "Asia/Dubai",
            "Asia/Tokyo",
        ]

    def _build_account_payload():
        profile = service.get_profile()
        notification_settings = service.get_notification_settings()
        return {
            "user": {
                "id": getattr(current_user, "id", None),
                "email": getattr(current_user, "email", ""),
            },
            "timezone_name": service.get_timezone_name(),
            "timezone_options": _timezone_options(),
            "notification_settings": notification_settings,
            "profile": profile,
        }

    @app.route("/api/settings/notifications", methods=["GET"])
    @auth_required()
    def get_notification_settings():
        return jsonify(service.get_notification_settings())

    @app.route("/api/daily-target", methods=["POST"])
    @auth_required()
    def set_daily_target_api():
        payload = _json_payload()
        service.set_daily_target(payload.get("target_seconds"))
        today = service.current_local_date()
        today_target_seconds = service.get_daily_target(today)
        return jsonify({"ok": True, "today_target_seconds": today_target_seconds})

    @app.route("/api/timer/dashboard", methods=["GET"])
    @auth_required()
    def timer_dashboard_api():
        return jsonify(_build_timer_dashboard_payload())

    @app.route("/api/calendar/board", methods=["GET"])
    @auth_required()
    def calendar_board_api():
        projects = service.list_projects()
        tasks = [
            task
            for task in service.list_tasks()
            if (task.get("status") or "active") != "completed"
        ]
        week_start, week_end = service.current_week_range()
        today = service.current_local_date()
        week_days = build_week_days(week_start, today)

        task_ids = [task["id"] for task in tasks]
        checks_map = service.list_task_daily_checks(task_ids, week_start, week_end)
        task_rows = []
        for task in tasks:
            checked_dates = checks_map.get(task["id"], set())
            week_checks = [day["iso"] in checked_dates for day in week_days]
            task_rows.append({**task, "week_checks": week_checks})

        habits_list = service.list_habits(today.isoformat())
        habit_ids = [habit["id"] for habit in habits_list]
        habit_logs_map = service.list_habit_logs_between(habit_ids, week_start, week_end)
        habit_rows = []
        for habit in habits_list:
            checked_dates = habit_logs_map.get(habit["id"], set())
            week_checks = [day["iso"] in checked_dates for day in week_days]
            habit_rows.append({**habit, "week_checks": week_checks})

        return jsonify(
            {
                "week_label": f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
                "week_days": week_days,
                "task_rows": task_rows,
                "habit_rows": habit_rows,
                "projects": projects,
            }
        )

    @app.route("/api/planner", methods=["GET"])
    @auth_required()
    def planner_api():
        return jsonify(_build_planner_payload())

    @app.route("/api/todos", methods=["POST"])
    @auth_required()
    def create_todo_api():
        payload = _json_payload()
        service.add_todo(payload.get("name", ""))
        return jsonify(_build_planner_payload())

    @app.route("/api/todos/<int:todo_id>/toggle", methods=["POST"])
    @auth_required()
    def toggle_todo_api(todo_id):
        payload = _json_payload()
        done = _coerce_bool(payload.get("done"))
        service.set_todo_done(todo_id, done)
        return jsonify(_build_planner_payload())

    @app.route("/api/todos/<int:todo_id>/delete", methods=["POST"])
    @auth_required()
    def delete_todo_api(todo_id):
        service.delete_todo(todo_id)
        return jsonify(_build_planner_payload())

    @app.route("/api/habits", methods=["GET"])
    @auth_required()
    def list_habits_api():
        return jsonify(_build_habits_payload())

    @app.route("/api/habits", methods=["POST"])
    @auth_required()
    def create_habit_api():
        payload = _json_payload()
        service.add_habit(
            payload.get("name", ""),
            payload.get("frequency", "Daily"),
            payload.get("time_of_day", ""),
            payload.get("reminder", ""),
            payload.get("notes", ""),
            payload.get("goal_name", ""),
            payload.get("subgoal_name", ""),
        )
        return jsonify(_build_habits_payload())

    @app.route("/api/habits/<int:habit_id>/toggle", methods=["POST"])
    @auth_required()
    def toggle_habit_api(habit_id):
        payload = _json_payload()
        log_date = payload.get("date") or service.current_local_date().isoformat()
        done = _coerce_bool(payload.get("done"))
        service.set_habit_done(habit_id, log_date, done)
        return jsonify(_build_habits_payload())

    @app.route("/api/habits/<int:habit_id>/update", methods=["POST"])
    @auth_required()
    def update_habit_api(habit_id):
        payload = _json_payload()
        service.update_habit(
            habit_id,
            payload.get("name", ""),
            payload.get("frequency", "Daily"),
            payload.get("time_of_day", ""),
            payload.get("reminder", ""),
            payload.get("notes", ""),
            payload.get("goal_name", ""),
            payload.get("subgoal_name", ""),
        )
        return jsonify(_build_habits_payload())

    @app.route("/api/habits/<int:habit_id>/delete", methods=["POST"])
    @auth_required()
    def delete_habit_api(habit_id):
        service.delete_habit(habit_id)
        return jsonify(_build_habits_payload())

    @app.route("/api/goals", methods=["GET"])
    @auth_required()
    def list_goals_api():
        return jsonify(_build_goals_payload())

    @app.route("/api/goals/<int:goal_id>", methods=["GET"])
    @auth_required()
    def goal_detail_api(goal_id):
        goal = service.get_goal(goal_id)
        if not goal:
            return jsonify({"error": "Goal not found"}), 404
        return jsonify(
            {
                "goal": goal,
                "projects": service.list_projects(),
                "tasks": service.list_tasks(),
                "labels": service.list_labels(),
            }
        )

    @app.route("/api/goals", methods=["POST"])
    @auth_required()
    def create_goal_api():
        payload = _json_payload()
        service.add_goal(
            payload.get("name", ""),
            payload.get("description", ""),
            payload.get("status", "active"),
            payload.get("priority", "medium"),
            payload.get("target_date", ""),
            payload.get("target_hours", 0),
            payload.get("label_id"),
            payload.get("subgoals", ""),
            _coerce_list(payload.get("project_ids")),
            _coerce_list(payload.get("task_ids")),
        )
        return jsonify(_build_goals_payload())

    @app.route("/api/goals/<int:goal_id>/edit", methods=["POST"])
    @auth_required()
    def edit_goal_api(goal_id):
        payload = _json_payload()
        service.update_goal(
            goal_id,
            payload.get("name", ""),
            payload.get("description", ""),
            payload.get("status", "active"),
            payload.get("priority", "medium"),
            payload.get("target_date", ""),
            payload.get("target_hours", 0),
            payload.get("label_id"),
            payload.get("subgoals"),
            _coerce_list(payload.get("project_ids")),
            _coerce_list(payload.get("task_ids")),
        )
        return jsonify(_build_goals_payload())

    @app.route("/api/goals/<int:goal_id>/delete", methods=["POST"])
    @auth_required()
    def delete_goal_api(goal_id):
        service.delete_goal(goal_id)
        return jsonify(_build_goals_payload())

    @app.route("/api/goals/subgoals/<int:subgoal_id>/toggle", methods=["POST"])
    @auth_required()
    def toggle_goal_subgoal_api(subgoal_id):
        payload = _json_payload()
        done = _coerce_bool(payload.get("done"))
        service.set_goal_subgoal_status(subgoal_id, done)
        return jsonify(_build_goals_payload())

    @app.route("/api/goals/<int:goal_id>/subgoals", methods=["POST"])
    @auth_required()
    def add_goal_subgoal_api(goal_id):
        payload = _json_payload()
        service.add_goal_subgoal(
            goal_id,
            payload.get("title", ""),
            payload.get("label", ""),
            payload.get("target_date", ""),
            payload.get("project_id", ""),
        )
        return jsonify(_build_goals_payload())

    @app.route("/api/weekly-goals", methods=["GET"])
    @auth_required()
    def weekly_goals_api():
        return jsonify(_build_weekly_goals_payload())

    @app.route("/api/weekly-goals", methods=["POST"])
    @auth_required()
    def create_weekly_goal_api():
        payload = _json_payload()
        week_start = payload.get("week_start")
        week_end = payload.get("week_end")
        if not week_start or not week_end:
            start_date, end_date = service.current_week_range()
            week_start = start_date.isoformat()
            week_end = end_date.isoformat()

        service.add_weekly_goal(
            payload.get("title", ""),
            payload.get("target_hours", 0),
            week_start,
            week_end,
            payload.get("long_term_goal_id"),
            payload.get("label_id"),
        )
        return jsonify(_build_weekly_goals_payload())

    @app.route("/api/weekly-goals/<int:goal_id>/toggle", methods=["POST"])
    @auth_required()
    def toggle_weekly_goal_api(goal_id):
        payload = _json_payload()
        status = payload.get("status", "active")
        service.toggle_weekly_goal_status(goal_id, status)
        return jsonify(_build_weekly_goals_payload())

    @app.route("/api/weekly-goals/<int:goal_id>/delete", methods=["POST"])
    @auth_required()
    def delete_weekly_goal_api(goal_id):
        service.delete_weekly_goal(goal_id)
        return jsonify(_build_weekly_goals_payload())

    @app.route("/api/reminders", methods=["GET"])
    @auth_required()
    def list_reminders_api():
        return jsonify(_build_reminders_payload())

    @app.route("/api/reminders", methods=["POST"])
    @auth_required()
    def create_reminder_api():
        payload = _json_payload()
        service.add_reminder(_to_multi_dict(payload))
        return jsonify(_build_reminders_payload())

    @app.route("/api/reminders/<int:reminder_id>/update", methods=["POST"])
    @auth_required()
    def update_reminder_api(reminder_id):
        payload = _json_payload()
        service.update_reminder(reminder_id, _to_multi_dict(payload))
        return jsonify(_build_reminders_payload())

    @app.route("/api/reminders/<int:reminder_id>/toggle", methods=["POST"])
    @auth_required()
    def toggle_reminder_api(reminder_id):
        payload = _json_payload()
        is_active = _coerce_bool(payload.get("is_active"))
        service.set_reminder_active(reminder_id, is_active)
        return jsonify(_build_reminders_payload())

    @app.route("/api/reminders/<int:reminder_id>/delete", methods=["POST"])
    @auth_required()
    def delete_reminder_api(reminder_id):
        service.delete_reminder(reminder_id)
        return jsonify(_build_reminders_payload())

    @app.route("/api/labels", methods=["GET"])
    @auth_required()
    def list_labels_api():
        return jsonify(_build_labels_payload())

    @app.route("/api/labels", methods=["POST"])
    @auth_required()
    def create_label_api():
        payload = _json_payload()
        service.add_label(payload.get("name", ""), payload.get("color", ""))
        return jsonify(_build_labels_payload())

    @app.route("/api/labels/<int:label_id>/edit", methods=["POST"])
    @auth_required()
    def edit_label_api(label_id):
        payload = _json_payload()
        service.update_label(label_id, payload.get("name", ""), payload.get("color", ""))
        return jsonify(_build_labels_payload())

    @app.route("/api/labels/<int:label_id>/delete", methods=["POST"])
    @auth_required()
    def delete_label_api(label_id):
        service.delete_label(label_id)
        return jsonify(_build_labels_payload())

    @app.route("/api/account", methods=["GET"])
    @auth_required()
    def account_api():
        return jsonify(_build_account_payload())

    @app.route("/api/settings/profile", methods=["POST"])
    @auth_required()
    def update_profile_api():
        payload = _json_payload()
        service.update_profile(_to_multi_dict(payload))
        return jsonify(_build_account_payload())

    @app.route("/api/settings/timezone", methods=["POST"])
    @auth_required()
    def update_timezone_api():
        payload = _json_payload()
        service.set_timezone_name(payload.get("timezone", "UTC"))
        return jsonify({"ok": True, "timezone_name": service.get_timezone_name()})

    @app.route("/api/settings/notifications", methods=["POST"])
    @auth_required()
    def update_notification_settings_api():
        payload = _json_payload()
        service.set_notification_settings(_to_multi_dict(payload))
        return jsonify(
            {
                "ok": True,
                "notification_settings": service.get_notification_settings(),
            }
        )

    @app.route("/api/reports/summary", methods=["GET"])
    @auth_required()
    def reports_summary():
        start = request.args.get("start")
        end = request.args.get("end")
        if not start or not end:
            return jsonify(
                {
                    "summary": [],
                    "distribution": [],
                    "total_seconds": 0,
                    "avg_daily_hours": 0,
                    "project_totals": [],
                    "active_projects": 0,
                    "top_project": None,
                    "entities": {},
                }
            )

        try:
            start_date = datetime.fromisoformat(start).date()
            end_date = datetime.fromisoformat(end).date()
        except ValueError:
            return jsonify(
                {
                    "summary": [],
                    "distribution": [],
                    "total_seconds": 0,
                    "avg_daily_hours": 0,
                    "project_totals": [],
                    "active_projects": 0,
                    "top_project": None,
                    "entities": {},
                }
            )

        if end_date < start_date:
            start_date, end_date = end_date, start_date

        summary = service.summary_by_range(start_date, end_date)
        group_by = request.args.get("group", "projects")
        if group_by not in {"projects", "labels", "tasks"}:
            group_by = "projects"

        distribution, total_seconds = service.distribution_by_range(
            start_date,
            end_date,
            group_by,
        )
        project_totals = service.project_totals_by_range(start_date, end_date)
        top_project = project_totals[0] if project_totals else None
        entities = service.report_entities_by_range(start_date, end_date)
        days = max((end_date - start_date).days + 1, 1)
        avg_daily_hours = total_seconds / 3600 / days

        return jsonify(
            {
                "summary": summary,
                "distribution": distribution,
                "total_seconds": total_seconds,
                "avg_daily_hours": avg_daily_hours,
                "project_totals": project_totals,
                "active_projects": len(project_totals),
                "top_project": top_project,
                "entities": entities,
            }
        )

    @app.route("/api/timer/entries", methods=["GET"])
    @auth_required()
    def timer_entries():
        start_raw = request.args.get("start")
        end_raw = request.args.get("end")
        start_dt = parse_iso(start_raw)
        end_dt = parse_iso(end_raw)
        if not start_dt or not end_dt:
            return jsonify({"events": []})
        if end_dt < start_dt:
            start_dt, end_dt = end_dt, start_dt
        events = service.list_time_entries_for_calendar(start_dt, end_dt)
        return jsonify({"events": events})

    @app.route("/api/tasks", methods=["GET"])
    @auth_required()
    def list_tasks_api():
        return jsonify(_build_tasks_payload())

    @app.route("/api/tasks", methods=["POST"])
    @auth_required()
    def create_task_api():
        payload = _json_payload()
        service.add_task(
            payload.get("name", ""),
            payload.get("project_id"),
            payload.get("label_ids", []),
            payload.get("goal_id"),
            payload.get("priority", "medium"),
        )
        return jsonify(_build_tasks_payload())

    @app.route("/api/tasks/<int:task_id>/start", methods=["POST"])
    @auth_required()
    def start_task_api(task_id):
        service.start_task(task_id)
        return jsonify(_build_tasks_payload())

    @app.route("/api/tasks/<int:task_id>/stop", methods=["POST"])
    @auth_required()
    def stop_task_api(task_id):
        service.stop_task(task_id)
        return jsonify(_build_tasks_payload())

    @app.route("/api/tasks/<int:task_id>/delete", methods=["POST"])
    @auth_required()
    def delete_task_api(task_id):
        service.delete_task(task_id)
        return jsonify(_build_tasks_payload())

    @app.route("/api/tasks/<int:task_id>/daily-check", methods=["POST"])
    @auth_required()
    def daily_check_task_api(task_id):
        payload = _json_payload()
        done = payload.get("done", True)
        service.set_task_daily_check(task_id, _coerce_bool(done))
        return jsonify(_build_tasks_payload())

    @app.route("/api/tasks/<int:task_id>/complete", methods=["POST"])
    @auth_required()
    def complete_task_api(task_id):
        service.set_task_status(task_id, "completed")
        return jsonify(_build_tasks_payload())

    @app.route("/api/tasks/<int:task_id>/reopen", methods=["POST"])
    @auth_required()
    def reopen_task_api(task_id):
        service.set_task_status(task_id, "active")
        return jsonify(_build_tasks_payload())

    @app.route("/api/tasks/bulk", methods=["POST"])
    @auth_required()
    def bulk_task_action_api():
        payload = _json_payload()
        task_ids = _parse_task_ids(payload.get("task_ids", []))
        if not task_ids:
            return jsonify(_build_tasks_payload())
        if not _run_bulk_task_action(task_ids, payload.get("action", "")):
            return jsonify({"error": "Invalid task action"}), 400
        return jsonify(_build_tasks_payload())

    @app.route("/api/tasks/<int:task_id>/edit", methods=["POST"])
    @auth_required()
    def edit_task_api(task_id):
        payload = _json_payload()
        service.update_task(task_id, payload.get("name", ""))
        label_id = payload.get("label_id")
        if label_id:
            try:
                service.add_label_to_task(task_id, int(label_id))
            except (TypeError, ValueError):
                pass
        return jsonify(_build_tasks_payload())

    @app.route("/api/tasks/<int:task_id>/labels", methods=["POST"])
    @auth_required()
    def add_task_label_api(task_id):
        payload = _json_payload()
        label_id = payload.get("label_id")
        if label_id:
            try:
                service.add_label_to_task(task_id, int(label_id))
            except (TypeError, ValueError):
                pass
        return jsonify(_build_tasks_payload())

    @app.route("/api/init", methods=["POST"])
    @auth_required()
    def init_api():
        service.init_db()
        return jsonify({"ok": True})

    @app.route("/api/projects", methods=["GET"])
    @auth_required()
    def list_projects_api():
        projects_list = service.list_projects()
        return jsonify(
            {
                "projects": [
                    {
                        "id": project["id"],
                        "name": project["name"],
                        "labels": project["labels"],
                    }
                    for project in projects_list
                ]
            }
        )

    @app.route("/api/projects", methods=["POST"])
    @auth_required()
    def create_project_api():
        payload = _json_payload()
        service.add_project(payload.get("name", ""), payload.get("label_ids", []))
        return list_projects_api()

    @app.route("/api/projects/<int:project_id>/edit", methods=["POST"])
    @auth_required()
    def edit_project_api(project_id):
        payload = _json_payload()
        service.update_project(
            project_id,
            payload.get("name", ""),
            _coerce_list(payload.get("label_ids")),
        )
        return list_projects_api()

    @app.route("/api/projects/<int:project_id>/labels", methods=["POST"])
    @auth_required()
    def add_project_label_api(project_id):
        payload = _json_payload()
        label_id = payload.get("label_id")
        if label_id:
            try:
                service.add_label_to_project(project_id, int(label_id))
            except (TypeError, ValueError):
                pass
        return list_projects_api()

    @app.route("/api/projects/<int:project_id>/delete", methods=["POST"])
    @auth_required()
    def delete_project_api(project_id):
        service.delete_project(project_id)
        return list_projects_api()
