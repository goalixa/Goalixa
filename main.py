import os
import sqlite3
from datetime import datetime
from flask import Flask, g, redirect, render_template, request, url_for

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "data.db")

app = Flask(__name__)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS time_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        );
        """
    )
    db.commit()


def fetch_tasks():
    db = get_db()
    tasks = db.execute(
        """
        SELECT t.id, t.name,
               IFNULL(SUM(
                   CASE
                       WHEN te.ended_at IS NULL THEN (strftime('%s','now') - strftime('%s', te.started_at))
                       ELSE (strftime('%s', te.ended_at) - strftime('%s', te.started_at))
                   END
               ), 0) AS total_seconds,
               MAX(CASE WHEN te.ended_at IS NULL THEN 1 ELSE 0 END) AS is_running
        FROM tasks t
        LEFT JOIN time_entries te ON te.task_id = t.id
        GROUP BY t.id
        ORDER BY t.created_at DESC
        """
    ).fetchall()
    return tasks


@app.route("/", methods=["GET"])
def index():
    tasks = fetch_tasks()
    return render_template("index.html", tasks=tasks)


@app.route("/tasks", methods=["POST"])
def create_task():
    name = request.form.get("name", "").strip()
    if name:
        db = get_db()
        db.execute(
            "INSERT INTO tasks (name, created_at) VALUES (?, ?)",
            (name, datetime.utcnow().isoformat()),
        )
        db.commit()
    return redirect(url_for("index"))


@app.route("/tasks/<int:task_id>/start", methods=["POST"])
def start_task(task_id):
    db = get_db()
    running = db.execute(
        "SELECT 1 FROM time_entries WHERE task_id = ? AND ended_at IS NULL", (task_id,)
    ).fetchone()
    if not running:
        db.execute(
            "INSERT INTO time_entries (task_id, started_at) VALUES (?, ?)",
            (task_id, datetime.utcnow().isoformat()),
        )
        db.commit()
    return redirect(url_for("index"))


@app.route("/tasks/<int:task_id>/stop", methods=["POST"])
def stop_task(task_id):
    db = get_db()
    db.execute(
        """
        UPDATE time_entries
        SET ended_at = ?
        WHERE task_id = ? AND ended_at IS NULL
        """,
        (datetime.utcnow().isoformat(), task_id),
    )
    db.commit()
    return redirect(url_for("index"))


@app.route("/init", methods=["POST"])
def init():
    init_db()
    return redirect(url_for("index"))


@app.template_filter("format_seconds")
def format_seconds(total_seconds):
    total_seconds = int(total_seconds or 0)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
