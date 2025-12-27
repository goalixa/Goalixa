from flask import redirect, render_template, request, url_for


def register_routes(app, service):
    @app.route("/", methods=["GET"])
    def index():
        tasks = service.list_tasks()
        return render_template("index.html", tasks=tasks)

    @app.route("/tasks", methods=["POST"])
    def create_task():
        service.add_task(request.form.get("name", ""))
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
                }
                for task in tasks
            ]
        }

    @app.route("/api/tasks", methods=["POST"])
    def create_task_api():
        payload = request.get_json(silent=True) or {}
        service.add_task(payload.get("name", ""))
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
