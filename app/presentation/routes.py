from datetime import datetime, timedelta, timezone

from flask import jsonify, redirect, render_template, request, url_for
from flask_security import auth_required


def register_routes(app, service):
    def parse_iso(value):
        if not value:
            return None
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    @app.route("/", methods=["GET"])
    @auth_required()
    def overview():
        summary = service.summary_by_days(7)
        return render_template(
            "overview.html",
            summary=summary,
            selected_range=7,
            allowed_ranges=[7],
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
                end_date = datetime.utcnow().date()
                start_date = end_date - timedelta(days=6)
        else:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=6)

        if end_date < start_date:
            start_date, end_date = end_date, start_date

        list_groups = service.list_time_entries_by_range(start_date, end_date)
        return render_template(
            "timer.html",
            timer_list_groups=list_groups,
            timer_range_start=start_date.isoformat(),
            timer_range_end=end_date.isoformat(),
        )

    @app.route("/calendar", methods=["GET"])
    @auth_required()
    def calendar():
        return render_template("calendar.html")

    @app.route("/reports", methods=["GET"])
    @auth_required()
    def reports():
        tasks = service.list_tasks()
        summary = service.summary_by_days(7)
        projects = {}
        for task in tasks:
            project_name = task.get("project_name") or "Unassigned"
            entry = projects.setdefault(
                project_name,
                {"name": project_name, "total_seconds": 0, "tasks": []},
            )
            entry["total_seconds"] += int(task.get("total_seconds") or 0)
            entry["tasks"].append(task)
        project_totals = sorted(
            projects.values(),
            key=lambda item: item["total_seconds"],
            reverse=True,
        )
        return render_template(
            "reports.html",
            tasks=tasks,
            summary=summary,
            project_totals=project_totals,
            allowed_ranges=[7],
        )

    @app.route("/api/reports/summary", methods=["GET"])
    @auth_required()
    def reports_summary():
        start = request.args.get("start")
        end = request.args.get("end")
        if not start or not end:
            return jsonify({"summary": [], "total_seconds": 0, "avg_daily_hours": 0})

        try:
            start_date = datetime.fromisoformat(start).date()
            end_date = datetime.fromisoformat(end).date()
        except ValueError:
            return jsonify({"summary": [], "total_seconds": 0, "avg_daily_hours": 0})

        if end_date < start_date:
            start_date, end_date = end_date, start_date

        summary = service.summary_by_range(start_date, end_date)
        group_by = request.args.get("group", "projects")
        if group_by not in {"projects", "labels", "tasks"}:
            group_by = "projects"
        distribution, total_seconds = service.distribution_by_range(
            start_date, end_date, group_by
        )
        days = max((end_date - start_date).days + 1, 1)
        avg_daily_hours = total_seconds / 3600 / days
        return jsonify(
            {
                "summary": summary,
                "distribution": distribution,
                "total_seconds": total_seconds,
                "avg_daily_hours": avg_daily_hours,
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
        tasks = service.list_tasks()
        projects = service.list_projects()
        labels = service.list_labels()
        return render_template(
            "index.html", tasks=tasks, projects=projects, labels=labels
        )

    @app.route("/tasks", methods=["POST"])
    @auth_required()
    def create_task():
        service.add_task(
            request.form.get("name", ""),
            request.form.get("project_id"),
            request.form.getlist("label_ids"),
        )
        return redirect(url_for("index"))

    @app.route("/api/tasks", methods=["GET"])
    @auth_required()
    def list_tasks():
        tasks = service.list_tasks()
        return {
            "tasks": [
                {
                    "id": task["id"],
                    "name": task["name"],
                    "total_seconds": int(task["total_seconds"] or 0),
                    "rolling_24h_seconds": int(task["rolling_24h_seconds"] or 0),
                    "is_running": bool(task["is_running"]),
                    "project_id": task["project_id"],
                    "project_name": task["project_name"],
                    "labels": task["labels"],
                }
                for task in tasks
            ]
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
        return render_template(
            "projects.html", projects=projects_list, labels=labels
        )

    @app.route("/projects/<int:project_id>", methods=["GET"])
    @auth_required()
    def project_detail(project_id):
        project = service.get_project(project_id)
        if project is None:
            return redirect(url_for("projects"))
        tasks = service.list_tasks_by_project(project_id)
        labels = service.list_labels()
        return render_template(
            "project_detail.html",
            project=project,
            tasks=tasks,
            labels=labels,
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
