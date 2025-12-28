from flask import redirect, render_template, request, url_for


def register_routes(app, service):
    @app.route("/", methods=["GET"])
    def overview():
        return render_template("overview.html")

    @app.route("/timer", methods=["GET"])
    def timer():
        return render_template("timer.html")

    @app.route("/tasks", methods=["GET"])
    def index():
        tasks = service.list_tasks()
        projects = service.list_projects()
        labels = service.list_labels()
        return render_template(
            "index.html", tasks=tasks, projects=projects, labels=labels
        )

    @app.route("/tasks", methods=["POST"])
    def create_task():
        service.add_task(
            request.form.get("name", ""),
            request.form.get("project_id"),
            request.form.getlist("label_ids"),
        )
        return redirect(url_for("index"))

    @app.route("/api/tasks", methods=["GET"])
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
    def create_task_api():
        payload = request.get_json(silent=True) or {}
        service.add_task(
            payload.get("name", ""),
            payload.get("project_id"),
            payload.get("label_ids", []),
        )
        return list_tasks()

    @app.route("/api/tasks/<int:task_id>/start", methods=["POST"])
    def start_task_api(task_id):
        service.start_task(task_id)
        return list_tasks()

    @app.route("/api/tasks/<int:task_id>/stop", methods=["POST"])
    def stop_task_api(task_id):
        service.stop_task(task_id)
        return list_tasks()

    @app.route("/api/tasks/<int:task_id>/delete", methods=["POST"])
    def delete_task_api(task_id):
        service.delete_task(task_id)
        return list_tasks()

    @app.route("/tasks/<int:task_id>/start", methods=["POST"])
    def start_task(task_id):
        service.start_task(task_id)
        return redirect(url_for("index"))

    @app.route("/tasks/<int:task_id>/stop", methods=["POST"])
    def stop_task(task_id):
        service.stop_task(task_id)
        return redirect(url_for("index"))

    @app.route("/tasks/<int:task_id>/delete", methods=["POST"])
    def delete_task(task_id):
        service.delete_task(task_id)
        return redirect(url_for("index"))

    @app.route("/tasks/<int:task_id>/labels", methods=["POST"])
    def add_task_label(task_id):
        label_id = request.form.get("label_id")
        if label_id:
            service.add_label_to_task(task_id, int(label_id))
        return redirect(request.referrer or url_for("index"))

    @app.route("/init", methods=["POST"])
    def init():
        service.init_db()
        return redirect(url_for("index"))

    @app.route("/projects", methods=["GET"])
    def projects():
        projects_list = service.list_projects()
        labels = service.list_labels()
        return render_template(
            "projects.html", projects=projects_list, labels=labels
        )

    @app.route("/projects/<int:project_id>", methods=["GET"])
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
    def create_project():
        service.add_project(
            request.form.get("name", ""),
            request.form.getlist("label_ids"),
        )
        return redirect(url_for("projects"))

    @app.route("/projects/<int:project_id>/delete", methods=["POST"])
    def delete_project(project_id):
        service.delete_project(project_id)
        return redirect(url_for("projects"))

    @app.route("/projects/<int:project_id>/labels", methods=["POST"])
    def add_project_label(project_id):
        label_id = request.form.get("label_id")
        if label_id:
            service.add_label_to_project(project_id, int(label_id))
        return redirect(url_for("project_detail", project_id=project_id))

    @app.route("/labels", methods=["GET"])
    def labels():
        labels_list = service.list_labels()
        return render_template("labels.html", labels=labels_list)

    @app.route("/labels", methods=["POST"])
    def create_label():
        service.add_label(request.form.get("name", ""), request.form.get("color", ""))
        return redirect(url_for("labels"))

    @app.route("/labels/<int:label_id>/delete", methods=["POST"])
    def delete_label(label_id):
        service.delete_label(label_id)
        return redirect(url_for("labels"))

    @app.route("/api/projects", methods=["GET"])
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
    def create_project_api():
        payload = request.get_json(silent=True) or {}
        service.add_project(payload.get("name", ""), payload.get("label_ids", []))
        return list_projects()

    @app.route("/api/projects/<int:project_id>/delete", methods=["POST"])
    def delete_project_api(project_id):
        service.delete_project(project_id)
        return list_projects()
