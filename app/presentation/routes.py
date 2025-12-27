from flask import redirect, render_template, request, url_for


def register_routes(app, service):
    @app.route("/", methods=["GET"])
    def index():
        tasks = service.list_tasks()
        projects = service.list_projects()
        return render_template("index.html", tasks=tasks, projects=projects)

    @app.route("/tasks", methods=["POST"])
    def create_task():
        service.add_task(
            request.form.get("name", ""),
            request.form.get("project_id"),
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
                    "is_running": bool(task["is_running"]),
                    "project_id": task["project_id"],
                    "project_name": task["project_name"],
                }
                for task in tasks
            ]
        }

    @app.route("/api/tasks", methods=["POST"])
    def create_task_api():
        payload = request.get_json(silent=True) or {}
        service.add_task(payload.get("name", ""), payload.get("project_id"))
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

    @app.route("/init", methods=["POST"])
    def init():
        service.init_db()
        return redirect(url_for("index"))

    @app.route("/projects", methods=["GET"])
    def projects():
        projects_list = service.list_projects()
        return render_template("projects.html", projects=projects_list)

    @app.route("/projects", methods=["POST"])
    def create_project():
        service.add_project(request.form.get("name", ""))
        return redirect(url_for("projects"))

    @app.route("/projects/<int:project_id>/delete", methods=["POST"])
    def delete_project(project_id):
        service.delete_project(project_id)
        return redirect(url_for("projects"))

    @app.route("/api/projects", methods=["GET"])
    def list_projects():
        projects_list = service.list_projects()
        return {
            "projects": [
                {"id": project["id"], "name": project["name"]}
                for project in projects_list
            ]
        }

    @app.route("/api/projects", methods=["POST"])
    def create_project_api():
        payload = request.get_json(silent=True) or {}
        service.add_project(payload.get("name", ""))
        return list_projects()

    @app.route("/api/projects/<int:project_id>/delete", methods=["POST"])
    def delete_project_api(project_id):
        service.delete_project(project_id)
        return list_projects()
