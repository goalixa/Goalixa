from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


from flask import jsonify, redirect, render_template, request, url_for
from app.auth_client import auth_required, current_user, url_for_security


def register_routes(app, service):
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
        for date in week_dates:
            day_label = date.strftime("%a")
            week_days.append(
                {
                    "iso": date.isoformat(),
                    "day": day_label,
                    "date": date.strftime("%d"),
                    "full": date.strftime("%b %d"),
                    "is_today": date == today,
                    "is_future": date > today,
                }
            )
        return week_days

    @app.before_request
    def load_user_context():
        if current_user.is_authenticated:
            service.repository.set_user_id(current_user.id)
            service.ensure_user_setup(current_user.email)
        else:
            service.repository.set_user_id(None)

    @app.route("/", methods=["GET"])
    @auth_required()
    def overview():
        return redirect(url_for("timer"))

    @app.route("/overview", methods=["GET"])
    @auth_required()
    def overview_page():
        today = service.current_local_date()
        start_date = today - timedelta(days=6)
        summary = service.summary_by_days(7)
        goals = service.list_goals()
        goals_in_progress = [
            goal for goal in goals if goal.get("status") in {"active", "at_risk"}
        ]
        total_goal_seconds = sum(goal.get("total_seconds", 0) for goal in goals)
        goals_targets_set = len([goal for goal in goals if goal.get("target_date")])

        habits_list = service.list_habits(today.isoformat())
        habits_summary = service.habits_summary(habits_list)
        habit_series = service.habit_completion_series(14)

        todo_view = service.list_todos_for_today()

        task_view = service.list_tasks_for_today()
        active_tasks = task_view["tasks"]
        done_today_tasks = task_view["done_today_tasks"]
        completed_tasks = task_view["completed_tasks"]
        running_tasks = sum(1 for task in active_tasks if task.get("is_running"))

        reminders_list = service.list_reminders()
        reminders_summary = service.reminders_summary(reminders_list)
        upcoming_reminders = sorted(
            [
                reminder
                for reminder in reminders_list
                if reminder.get("is_active") and reminder.get("next_at")
            ],
            key=lambda reminder: reminder["next_at"],
        )[:3]

        project_distribution, project_distribution_total = (
            service.project_distribution_by_range(start_date, today)
        )
        top_project = project_distribution[0] if project_distribution else None

        calendar_entries = service.list_time_entries_by_range(start_date, today)
        calendar_entry_count = sum(
            len(bucket.get("entries", [])) for bucket in calendar_entries
        )
        calendar_active_days = len(calendar_entries)

        projects = service.list_projects()
        labels = service.list_labels()

        week_start, week_end = service.current_week_range()
        weekly_goals = service.list_weekly_goals(
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
        )
        weekly_active_goals = sum(
            1 for goal in weekly_goals if goal.get("status") == "active"
        )
        weekly_completed_goals = sum(
            1 for goal in weekly_goals if goal.get("status") == "completed"
        )
        weekly_avg_progress = (
            int(
                sum(goal.get("progress_percent", 0) for goal in weekly_goals)
                / len(weekly_goals)
            )
            if weekly_goals
            else 0
        )

        week_total_seconds = sum(bucket.get("seconds", 0) for bucket in summary)
        today_seconds = summary[-1]["seconds"] if summary else 0
        avg_daily_hours = week_total_seconds / 3600 / 7 if summary else 0

        linked_projects_total = sum(goal.get("projects_count", 0) for goal in goals)
        linked_tasks_total = sum(goal.get("tasks_count", 0) for goal in goals)

        timezone_name = service.get_timezone_name()
        notification_settings = service.get_notification_settings()
        return render_template(
            "overview.html",
            summary=summary,
            goals=goals,
            goals_in_progress=goals_in_progress,
            active_goals_count=len(goals_in_progress),
            total_goal_seconds=total_goal_seconds,
            goals_targets_set=goals_targets_set,
            selected_range=7,
            allowed_ranges=[7],
            today_date=today.isoformat(),
            habits=habits_list,
            habits_summary=habits_summary,
            habit_series=habit_series,
            todos=todo_view["todos"],
            done_todos=todo_view["done_todos"],
            active_tasks=active_tasks,
            done_today_tasks=done_today_tasks,
            completed_tasks=completed_tasks,
            running_tasks=running_tasks,
            reminders=reminders_list,
            reminders_summary=reminders_summary,
            upcoming_reminders=upcoming_reminders,
            project_distribution=project_distribution,
            project_distribution_total=project_distribution_total,
            top_project=top_project,
            calendar_entry_count=calendar_entry_count,
            calendar_active_days=calendar_active_days,
            projects=projects,
            labels=labels,
            weekly_goals=weekly_goals,
            weekly_active_goals=weekly_active_goals,
            weekly_completed_goals=weekly_completed_goals,
            weekly_avg_progress=weekly_avg_progress,
            week_range_label=f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
            week_total_seconds=week_total_seconds,
            today_seconds=today_seconds,
            avg_daily_hours=avg_daily_hours,
            linked_projects_total=linked_projects_total,
            linked_tasks_total=linked_tasks_total,
            timezone_name=timezone_name,
            notification_settings=notification_settings,
            user_email=getattr(current_user, "email", ""),
        )

    @app.route("/timer", methods=["GET"])
    @auth_required()
    def timer():
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

        list_groups = service.list_time_entries_by_range(start_date, end_date)

        # Calculate today's total
        today = service.current_local_date()
        today_total_seconds = 0
        for group in list_groups:
            if group["label"] == "Today":
                today_total_seconds = group["total_seconds"]
                break

        # Calculate week total
        week_start, week_end = service.current_week_range()
        week_total_seconds = 0
        week_groups = service.list_time_entries_by_range(week_start, week_end)
        for group in week_groups:
            week_total_seconds += group["total_seconds"]

        tasks = service.list_tasks()
        week_days = build_week_days(week_start, today)
        task_ids = [task["id"] for task in tasks]
        checks_map = service.list_task_daily_checks(task_ids, week_start, week_end)
        task_rows = []
        for task in tasks:
            checked_dates = checks_map.get(task["id"], set())
            week_checks = [day["iso"] in checked_dates for day in week_days]
            task_rows.append({**task, "week_checks": week_checks})
        week_label = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}"

        return render_template(
            "timer.html",
            timer_list_groups=list_groups,
            timer_range_start=start_date.isoformat(),
            timer_range_end=end_date.isoformat(),
            today_total_seconds=today_total_seconds,
            week_total_seconds=week_total_seconds,
            week_label=week_label,
            week_days=week_days,
            task_rows=task_rows,
        )

    @app.route("/calendar", methods=["GET"])
    @auth_required()
    def calendar():
        projects = service.list_projects()
        tasks = service.list_tasks()
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
        week_label = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}"
        return render_template(
            "calendar.html",
            week_label=week_label,
            week_days=week_days,
            task_rows=task_rows,
            projects=projects,
        )

    @app.route("/habits", methods=["GET"])
    @auth_required()
    def habits():
        today = service.current_local_date().isoformat()
        habits_list = service.list_habits(today)
        summary = service.habits_summary(habits_list)
        goals_list = service.list_goals()
        series = service.habit_completion_series(14)
        return render_template(
            "habits.html",
            habits=habits_list,
            goals=goals_list,
            total_habits=summary["total"],
            completed_habits=summary["completed"],
            best_streak=summary["best_streak"],
            focus_window=summary["focus_window"],
            today=today,
            habit_series=series,
        )

    @app.route("/planner", methods=["GET"])
    @auth_required()
    def planner():
        today = service.current_local_date().isoformat()
        habits_list = service.list_habits(today)
        summary = service.habits_summary(habits_list)
        todo_view = service.list_todos_for_today()
        return render_template(
            "planner.html",
            habits=habits_list,
            habits_summary=summary,
            todos=todo_view["todos"],
            done_todos=todo_view["done_todos"],
            today=today,
        )

    @app.route("/reminders", methods=["GET"])
    @auth_required()
    def reminders():
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
        return render_template(
            "reminders.html",
            reminders=reminders_list,
            reminders_summary=summary,
            notification_settings=notification_settings,
            today=today,
            weekday_options=weekday_options,
        )

    @app.route("/reminders", methods=["POST"])
    @auth_required()
    def create_reminder():
        service.add_reminder(request.form)
        return redirect(url_for("reminders"))

    @app.route("/reminders/<int:reminder_id>/update", methods=["POST"])
    @auth_required()
    def update_reminder(reminder_id):
        service.update_reminder(reminder_id, request.form)
        return redirect(url_for("reminders"))

    @app.route("/reminders/<int:reminder_id>/toggle", methods=["POST"])
    @auth_required()
    def toggle_reminder(reminder_id):
        is_active = request.form.get("is_active") in {"1", "true", "on", "yes"}
        service.set_reminder_active(reminder_id, is_active)
        return redirect(url_for("reminders"))

    @app.route("/reminders/<int:reminder_id>/delete", methods=["POST"])
    @auth_required()
    def delete_reminder(reminder_id):
        service.delete_reminder(reminder_id)
        return redirect(url_for("reminders"))

    @app.errorhandler(400)
    def handle_bad_request(error):
        return render_template(
            "error.html",
            title="Bad request",
            status_code=400,
            message="We could not process that request.",
            details=str(error),
        ), 400

    @app.errorhandler(401)
    def handle_unauthorized(error):
        return render_template(
            "error.html",
            title="Unauthorized",
            status_code=401,
            message="Please sign in to continue.",
            details=str(error),
            action_url=url_for_security("login"),
            action_label="Sign in",
        ), 401

    @app.errorhandler(403)
    def handle_forbidden(error):
        return render_template(
            "error.html",
            title="Access denied",
            status_code=403,
            message="You do not have access to this page.",
            details=str(error),
        ), 403

    @app.errorhandler(404)
    def handle_not_found(error):
        return render_template(
            "error.html",
            title="Not found",
            status_code=404,
            message="We could not find that page.",
            details=str(error),
        ), 404

    @app.errorhandler(500)
    def handle_server_error(error):
        return render_template(
            "error.html",
            title="Server error",
            status_code=500,
            message="Something went wrong on our side.",
            details=str(error),
        ), 500

    @app.route("/habits", methods=["POST"])
    @auth_required()
    def create_habit():
        service.add_habit(
            request.form.get("name", ""),
            request.form.get("frequency", "Daily"),
            request.form.get("time_of_day", ""),
            request.form.get("reminder", ""),
            request.form.get("notes", ""),
            request.form.get("goal_name", ""),
            request.form.get("subgoal_name", ""),
        )
        return redirect(request.referrer or url_for("habits"))

    @app.route("/habits/<int:habit_id>/toggle", methods=["POST"])
    @auth_required()
    def toggle_habit(habit_id):
        log_date = request.form.get("date") or service.current_local_date().isoformat()
        done = request.form.get("done") in {"1", "on", "true"}
        service.set_habit_done(habit_id, log_date, done)
        return redirect(request.referrer or url_for("habits"))

    @app.route("/habits/<int:habit_id>/update", methods=["POST"])
    @auth_required()
    def update_habit(habit_id):
        service.update_habit(
            habit_id,
            request.form.get("name", ""),
            request.form.get("frequency", "Daily"),
            request.form.get("time_of_day", ""),
            request.form.get("reminder", ""),
            request.form.get("notes", ""),
            request.form.get("goal_name", ""),
            request.form.get("subgoal_name", ""),
        )
        return redirect(request.referrer or url_for("habits"))

    @app.route("/habits/<int:habit_id>/delete", methods=["POST"])
    @auth_required()
    def delete_habit(habit_id):
        service.delete_habit(habit_id)
        return redirect(request.referrer or url_for("habits"))

    @app.route("/todos", methods=["POST"])
    @auth_required()
    def create_todo():
        service.add_todo(request.form.get("name", ""))
        return redirect(request.referrer or url_for("planner"))

    @app.route("/todos/<int:todo_id>/toggle", methods=["POST"])
    @auth_required()
    def toggle_todo(todo_id):
        done = request.form.get("done") in {"1", "on", "true"}
        service.set_todo_done(todo_id, done)
        return redirect(request.referrer or url_for("planner"))

    @app.route("/todos/<int:todo_id>/delete", methods=["POST"])
    @auth_required()
    def delete_todo(todo_id):
        service.delete_todo(todo_id)
        return redirect(request.referrer or url_for("planner"))

    @app.route("/goals", methods=["GET"])
    @auth_required()
    def goals():
        goals_list = service.list_goals()
        active_goals = [goal for goal in goals_list if goal.get("status") in {"active", "at_risk"}]
        total_goal_seconds = sum(goal.get("total_seconds", 0) for goal in goals_list)
        targets_set = len([goal for goal in goals_list if goal.get("target_date")])
        week_start, week_end = service.current_week_range()
        weekly_goals = service.list_weekly_goals(
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
        )
        return render_template(
            "goals.html",
            goals=goals_list,
            active_goals_count=len(active_goals),
            total_goal_seconds=total_goal_seconds,
            targets_set=targets_set,
            weekly_goals=weekly_goals,
            weekly_range_label=f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
        )

    @app.route("/long-term-goals", methods=["GET"])
    @auth_required()
    def long_term_goals():
        goals_list = service.list_goals()
        projects = service.list_projects()
        tasks = service.list_tasks()
        active_goals = [goal for goal in goals_list if goal.get("status") in {"active", "at_risk"}]
        return render_template(
            "long_term_goals.html",
            goals=goals_list,
            projects=projects,
            tasks=tasks,
            active_goals_count=len(active_goals),
        )

    @app.route("/goals/<int:goal_id>", methods=["GET"])
    @auth_required()
    def goal_detail(goal_id):
        goal = service.get_goal(goal_id)
        if not goal:
            return redirect(url_for("goals"))
        projects = service.list_projects()
        return render_template(
            "goal_detail.html",
            goal=goal,
            projects=projects,
        )

    @app.route("/goals/new", methods=["GET"])
    @auth_required()
    def new_goal():
        projects = service.list_projects()
        tasks = service.list_tasks()
        return render_template(
            "goals_new.html",
            projects=projects,
            tasks=tasks,
        )

    @app.route("/goals", methods=["POST"])
    @auth_required()
    def create_goal():
        service.add_goal(
            request.form.get("name", ""),
            request.form.get("description", ""),
            request.form.get("status", "active"),
            request.form.get("priority", "medium"),
            request.form.get("target_date", ""),
            request.form.get("target_hours", 0),
            request.form.get("subgoals", ""),
            request.form.getlist("project_ids"),
            request.form.getlist("task_ids"),
        )
        return redirect(url_for("goals"))

    @app.route("/goals/<int:goal_id>/edit", methods=["POST"])
    @auth_required()
    def edit_goal(goal_id):
        service.update_goal(
            goal_id,
            request.form.get("name", ""),
            request.form.get("description", ""),
            request.form.get("status", "active"),
            request.form.get("priority", "medium"),
            request.form.get("target_date", ""),
            request.form.get("target_hours", 0),
            request.form.get("subgoals"),
            request.form.getlist("project_ids"),
            request.form.getlist("task_ids"),
        )
        return redirect(url_for("goals"))

    @app.route("/goals/subgoals/<int:subgoal_id>/toggle", methods=["POST"])
    @auth_required()
    def toggle_goal_subgoal(subgoal_id):
        done = request.form.get("done") == "on"
        service.set_goal_subgoal_status(subgoal_id, done)
        return redirect(request.referrer or url_for("goals"))

    @app.route("/goals/<int:goal_id>/subgoals", methods=["POST"])
    @auth_required()
    def add_goal_subgoal(goal_id):
        service.add_goal_subgoal(
            goal_id,
            request.form.get("title", ""),
            request.form.get("label", ""),
            request.form.get("target_date", ""),
            request.form.get("project_id", ""),
        )
        return redirect(request.referrer or url_for("goals"))

    @app.route("/goals/<int:goal_id>/delete", methods=["POST"])
    @auth_required()
    def delete_goal(goal_id):
        service.delete_goal(goal_id)
        return redirect(url_for("goals"))

    @app.route("/weekly-goals", methods=["GET"])
    @auth_required()
    def weekly_goals():
        week_start, week_end = service.current_week_range()
        weekly_current = service.list_weekly_goals(
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
        )
        weekly_all = service.list_weekly_goals()
        return render_template(
            "weekly_goals.html",
            weekly_goals_current=weekly_current,
            weekly_goals_all=weekly_all,
            weekly_range_label=f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
        )

    @app.route("/weekly-goals", methods=["POST"])
    @auth_required()
    def create_weekly_goal():
        week_start = request.form.get("week_start")
        week_end = request.form.get("week_end")
        if not week_start or not week_end:
            start_date, end_date = service.current_week_range()
            week_start = start_date.isoformat()
            week_end = end_date.isoformat()
        service.add_weekly_goal(
            request.form.get("title", ""),
            request.form.get("target_hours", 0),
            week_start,
            week_end,
        )
        return redirect(request.referrer or url_for("weekly_goals"))

    @app.route("/weekly-goals/<int:goal_id>/toggle", methods=["POST"])
    @auth_required()
    def toggle_weekly_goal(goal_id):
        status = request.form.get("status", "active")
        service.toggle_weekly_goal_status(goal_id, status)
        return redirect(request.referrer or url_for("weekly_goals"))

    @app.route("/weekly-goals/<int:goal_id>/delete", methods=["POST"])
    @auth_required()
    def delete_weekly_goal(goal_id):
        service.delete_weekly_goal(goal_id)
        return redirect(request.referrer or url_for("weekly_goals"))

    @app.route("/account", methods=["GET"])
    @auth_required()
    def account():
        timezone_options = [
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
        notification_settings = service.get_notification_settings()
        return render_template(
            "account.html",
            user=current_user,
            timezone_name=service.get_timezone_name(),
            timezone_options=timezone_options,
            notification_settings=notification_settings,
        )

    @app.route("/settings/timezone", methods=["POST"])
    @auth_required()
    def update_timezone():
        service.set_timezone_name(request.form.get("timezone", "UTC"))
        return redirect(url_for("account"))

    @app.route("/settings/notifications", methods=["POST"])
    @auth_required()
    def update_notifications():
        service.set_notification_settings(request.form)
        return redirect(url_for("account"))

    @app.route("/api/settings/notifications", methods=["GET"])
    @auth_required()
    def get_notification_settings():
        return jsonify(service.get_notification_settings())

    @app.route("/reports", methods=["GET"])
    @auth_required()
    def reports():
        end_date = service.current_local_date()
        start_date = end_date - timedelta(days=6)
        summary = service.summary_by_range(start_date, end_date)
        project_totals = service.project_totals_by_range(start_date, end_date)
        top_project = project_totals[0] if project_totals else None
        report_entities = service.report_entities_by_range(start_date, end_date)
        return render_template(
            "reports.html",
            summary=summary,
            project_totals=project_totals,
            top_project=top_project,
            report_entities=report_entities,
            allowed_ranges=[7],
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
            start_date, end_date, group_by
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

    @app.route("/tasks", methods=["GET"])
    @auth_required()
    def index():
        task_view = service.list_tasks_for_today()
        projects = service.list_projects()
        labels = service.list_labels()
        return render_template(
            "index.html",
            tasks=task_view["tasks"],
            done_today_tasks=task_view["done_today_tasks"],
            completed_tasks=task_view["completed_tasks"],
            projects=projects,
            labels=labels,
        )

    @app.route("/tasks", methods=["POST"])
    @auth_required()
    def create_task():
        service.add_task(
            request.form.get("name", ""),
            request.form.get("project_id"),
            request.form.getlist("label_ids"),
        )
        return redirect(request.referrer or url_for("index"))

    @app.route("/api/tasks", methods=["GET"])
    @auth_required()
    def list_tasks():
        task_view = service.list_tasks_for_today()
        return {
            "tasks": [
                {
                    "id": task["id"],
                    "name": task["name"],
                    "total_seconds": int(task["total_seconds"] or 0),
                    "rolling_24h_seconds": int(task["rolling_24h_seconds"] or 0),
                    "today_seconds": int(task.get("today_seconds") or 0),
                    "is_running": bool(task["is_running"]),
                    "project_id": task["project_id"],
                    "project_name": task["project_name"],
                    "labels": task["labels"],
                    "status": task.get("status") or "active",
                    "checked_today": bool(task.get("checked_today")),
                    "daily_checks": int(task.get("daily_checks") or 0),
                    "completed_at": task.get("completed_at"),
                }
                for task in task_view["tasks"]
            ],
            "done_today_tasks": [
                {
                    "id": task["id"],
                    "name": task["name"],
                    "total_seconds": int(task["total_seconds"] or 0),
                    "rolling_24h_seconds": int(task["rolling_24h_seconds"] or 0),
                    "today_seconds": int(task.get("today_seconds") or 0),
                    "is_running": bool(task["is_running"]),
                    "project_id": task["project_id"],
                    "project_name": task["project_name"],
                    "labels": task["labels"],
                    "status": task.get("status") or "active",
                    "checked_today": bool(task.get("checked_today")),
                    "daily_checks": int(task.get("daily_checks") or 0),
                    "completed_at": task.get("completed_at"),
                }
                for task in task_view["done_today_tasks"]
            ],
            "completed_tasks": [
                {
                    "id": task["id"],
                    "name": task["name"],
                    "total_seconds": int(task["total_seconds"] or 0),
                    "rolling_24h_seconds": int(task["rolling_24h_seconds"] or 0),
                    "today_seconds": int(task.get("today_seconds") or 0),
                    "is_running": bool(task["is_running"]),
                    "project_id": task["project_id"],
                    "project_name": task["project_name"],
                    "labels": task["labels"],
                    "status": task.get("status") or "active",
                    "checked_today": bool(task.get("checked_today")),
                    "daily_checks": int(task.get("daily_checks") or 0),
                    "completed_at": task.get("completed_at"),
                }
                for task in task_view["completed_tasks"]
            ],
        }

    @app.route("/api/tasks", methods=["POST"])
    @auth_required()
    def create_task_api():
        payload = request.get_json(silent=True) or {}
        service.add_task(
            payload.get("name", ""),
            payload.get("project_id"),
            payload.get("label_ids", []),
        )
        return list_tasks()

    @app.route("/api/tasks/<int:task_id>/start", methods=["POST"])
    @auth_required()
    def start_task_api(task_id):
        service.start_task(task_id)
        return list_tasks()

    @app.route("/api/tasks/<int:task_id>/stop", methods=["POST"])
    @auth_required()
    def stop_task_api(task_id):
        service.stop_task(task_id)
        return list_tasks()

    @app.route("/api/tasks/<int:task_id>/delete", methods=["POST"])
    @auth_required()
    def delete_task_api(task_id):
        service.delete_task(task_id)
        return list_tasks()

    @app.route("/api/tasks/<int:task_id>/daily-check", methods=["POST"])
    @auth_required()
    def daily_check_task_api(task_id):
        service.set_task_daily_check(task_id, True)
        return list_tasks()

    @app.route("/api/tasks/<int:task_id>/complete", methods=["POST"])
    @auth_required()
    def complete_task_api(task_id):
        service.set_task_status(task_id, "completed")
        return list_tasks()

    @app.route("/api/tasks/<int:task_id>/reopen", methods=["POST"])
    @auth_required()
    def reopen_task_api(task_id):
        service.set_task_status(task_id, "active")
        return list_tasks()

    @app.route("/tasks/<int:task_id>/start", methods=["POST"])
    @auth_required()
    def start_task(task_id):
        service.start_task(task_id)
        return redirect(url_for("index"))

    @app.route("/tasks/<int:task_id>/stop", methods=["POST"])
    @auth_required()
    def stop_task(task_id):
        service.stop_task(task_id)
        return redirect(url_for("index"))

    @app.route("/tasks/<int:task_id>/delete", methods=["POST"])
    @auth_required()
    def delete_task(task_id):
        service.delete_task(task_id)
        return redirect(url_for("index"))

    @app.route("/tasks/<int:task_id>/daily-check", methods=["POST"])
    @auth_required()
    def daily_check_task(task_id):
        service.set_task_daily_check(task_id, True)
        return redirect(request.referrer or url_for("index"))

    @app.route("/tasks/<int:task_id>/complete", methods=["POST"])
    @auth_required()
    def complete_task(task_id):
        service.set_task_status(task_id, "completed")
        return redirect(request.referrer or url_for("index"))

    @app.route("/tasks/<int:task_id>/reopen", methods=["POST"])
    @auth_required()
    def reopen_task(task_id):
        service.set_task_status(task_id, "active")
        return redirect(request.referrer or url_for("index"))

    @app.route("/tasks/<int:task_id>/edit", methods=["POST"])
    @auth_required()
    def edit_task(task_id):
        service.update_task(task_id, request.form.get("name", ""))
        label_id = request.form.get("label_id")
        if label_id:
            service.add_label_to_task(task_id, int(label_id))
        return redirect(request.referrer or url_for("index"))

    @app.route("/tasks/<int:task_id>/labels", methods=["POST"])
    @auth_required()
    def add_task_label(task_id):
        label_id = request.form.get("label_id")
        if label_id:
            service.add_label_to_task(task_id, int(label_id))
        return redirect(request.referrer or url_for("index"))

    @app.route("/init", methods=["POST"])
    @auth_required()
    def init():
        service.init_db()
        return redirect(url_for("index"))

    @app.route("/projects", methods=["GET"])
    @auth_required()
    def projects():
        projects_list = service.list_projects()
        labels = service.list_labels()
        tasks = service.list_tasks()
        active_task_count = len(
            [task for task in tasks if task.get("status") != "completed"]
        )
        total_focus_seconds = sum(
            task.get("total_seconds", 0) for task in tasks
        )
        return render_template(
            "projects.html",
            projects=projects_list,
            labels=labels,
            active_task_count=active_task_count,
            total_focus_seconds=total_focus_seconds,
            label_count=len(labels),
        )

    @app.route("/projects/<int:project_id>", methods=["GET"])
    @auth_required()
    def project_detail(project_id):
        project = service.get_project(project_id)
        if project is None:
            return redirect(url_for("projects"))
        tasks = service.list_tasks_by_project(project_id)
        labels = service.list_labels()
        active_tasks = [task for task in tasks if task.get("status") != "completed"]
        completed_tasks = [task for task in tasks if task.get("status") == "completed"]
        total_focus_seconds = sum(task.get("total_seconds", 0) for task in tasks)
        return render_template(
            "project_detail.html",
            project=project,
            tasks=tasks,
            labels=labels,
            active_task_count=len(active_tasks),
            completed_task_count=len(completed_tasks),
            total_focus_seconds=total_focus_seconds,
        )

    @app.route("/projects", methods=["POST"])
    @auth_required()
    def create_project():
        service.add_project(
            request.form.get("name", ""),
            request.form.getlist("label_ids"),
        )
        return redirect(url_for("projects"))

    @app.route("/projects/<int:project_id>/delete", methods=["POST"])
    @auth_required()
    def delete_project(project_id):
        service.delete_project(project_id)
        return redirect(url_for("projects"))

    @app.route("/projects/<int:project_id>/edit", methods=["POST"])
    @auth_required()
    def edit_project(project_id):
        service.update_project(
            project_id,
            request.form.get("name", ""),
            request.form.getlist("label_ids"),
        )
        return redirect(request.referrer or url_for("projects"))

    @app.route("/projects/<int:project_id>/labels", methods=["POST"])
    @auth_required()
    def add_project_label(project_id):
        label_id = request.form.get("label_id")
        if label_id:
            service.add_label_to_project(project_id, int(label_id))
        return redirect(url_for("project_detail", project_id=project_id))

    @app.route("/labels", methods=["GET"])
    @auth_required()
    def labels():
        labels_list = service.list_labels()
        return render_template("labels.html", labels=labels_list)

    @app.route("/labels", methods=["POST"])
    @auth_required()
    def create_label():
        service.add_label(request.form.get("name", ""), request.form.get("color", ""))
        return redirect(url_for("labels"))

    @app.route("/labels/<int:label_id>/delete", methods=["POST"])
    @auth_required()
    def delete_label(label_id):
        service.delete_label(label_id)
        return redirect(url_for("labels"))

    @app.route("/labels/<int:label_id>/edit", methods=["POST"])
    @auth_required()
    def edit_label(label_id):
        service.update_label(
            label_id,
            request.form.get("name", ""),
            request.form.get("color", ""),
        )
        return redirect(url_for("labels"))

    @app.route("/api/projects", methods=["GET"])
    @auth_required()
    def list_projects():
        projects_list = service.list_projects()
        return {
            "projects": [
                {
                    "id": project["id"],
                    "name": project["name"],
                    "labels": project["labels"],
                }
                for project in projects_list
            ]
        }

    @app.route("/api/projects", methods=["POST"])
    @auth_required()
    def create_project_api():
        payload = request.get_json(silent=True) or {}
        service.add_project(payload.get("name", ""), payload.get("label_ids", []))
        return list_projects()

    @app.route("/api/projects/<int:project_id>/delete", methods=["POST"])
    @auth_required()
    def delete_project_api(project_id):
        service.delete_project(project_id)
        return list_projects()
