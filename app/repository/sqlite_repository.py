import sqlite3

from flask import g


class SQLiteTaskRepository:
    def __init__(self, db_path):
        self.db_path = db_path

    def _get_db(self):
        if "db" not in g:
            g.db = sqlite3.connect(self.db_path)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    def close_db(self, exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db(self):
        db = self._get_db()
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS project_labels (
                project_id INTEGER NOT NULL,
                label_id INTEGER NOT NULL,
                PRIMARY KEY (project_id, label_id),
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (label_id) REFERENCES labels (id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                project_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS task_labels (
                task_id INTEGER NOT NULL,
                label_id INTEGER NOT NULL,
                PRIMARY KEY (task_id, label_id),
                FOREIGN KEY (task_id) REFERENCES tasks (id),
                FOREIGN KEY (label_id) REFERENCES labels (id)
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
        columns = db.execute("PRAGMA table_info(tasks)").fetchall()
        column_names = {column["name"] for column in columns}
        if "project_id" not in column_names:
            db.execute("ALTER TABLE tasks ADD COLUMN project_id INTEGER")
        db.commit()

    def ensure_default_project(self, name, created_at):
        db = self._get_db()
        db.execute(
            "INSERT OR IGNORE INTO projects (name, created_at) VALUES (?, ?)",
            (name, created_at),
        )
        row = db.execute(
            "SELECT id FROM projects WHERE name = ?",
            (name,),
        ).fetchone()
        return row["id"] if row else None

    def backfill_tasks_project(self, project_id):
        db = self._get_db()
        db.execute(
            "UPDATE tasks SET project_id = ? WHERE project_id IS NULL OR project_id = 0",
            (project_id,),
        )
        db.commit()
        db.commit()

    def fetch_tasks(self):
        db = self._get_db()
        tasks = db.execute(
            """
            WITH params AS (
                SELECT
                    CAST(strftime('%s','now') AS INTEGER) AS now_ts,
                    CAST(strftime('%s','now','-24 hours') AS INTEGER) AS window_start
            )
            SELECT t.id, t.name, t.project_id, p.name AS project_name,
                   IFNULL(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           WHEN te.ended_at IS NULL THEN (strftime('%s','now') - strftime('%s', te.started_at))
                           ELSE (strftime('%s', te.ended_at) - strftime('%s', te.started_at))
                       END
                   ), 0) AS total_seconds,
                   IFNULL(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           ELSE MAX(
                               0,
                               MIN(
                                   COALESCE(strftime('%s', te.ended_at), params.now_ts),
                                   params.now_ts
                               ) - MAX(strftime('%s', te.started_at), params.window_start)
                           )
                       END
                   ), 0) AS rolling_24h_seconds,
                   MAX(CASE WHEN te.id IS NOT NULL AND te.ended_at IS NULL THEN 1 ELSE 0 END) AS is_running
            FROM tasks t
            CROSS JOIN params
            LEFT JOIN projects p ON p.id = t.project_id
            LEFT JOIN time_entries te ON te.task_id = t.id
            GROUP BY t.id
            ORDER BY t.created_at DESC
            """
        ).fetchall()
        return tasks

    def fetch_tasks_by_project(self, project_id):
        db = self._get_db()
        tasks = db.execute(
            """
            WITH params AS (
                SELECT
                    CAST(strftime('%s','now') AS INTEGER) AS now_ts,
                    CAST(strftime('%s','now','-24 hours') AS INTEGER) AS window_start
            )
            SELECT t.id, t.name, t.project_id, p.name AS project_name,
                   IFNULL(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           WHEN te.ended_at IS NULL THEN (strftime('%s','now') - strftime('%s', te.started_at))
                           ELSE (strftime('%s', te.ended_at) - strftime('%s', te.started_at))
                       END
                   ), 0) AS total_seconds,
                   IFNULL(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           ELSE MAX(
                               0,
                               MIN(
                                   COALESCE(strftime('%s', te.ended_at), params.now_ts),
                                   params.now_ts
                               ) - MAX(strftime('%s', te.started_at), params.window_start)
                           )
                       END
                   ), 0) AS rolling_24h_seconds,
                   MAX(CASE WHEN te.id IS NOT NULL AND te.ended_at IS NULL THEN 1 ELSE 0 END) AS is_running
            FROM tasks t
            CROSS JOIN params
            LEFT JOIN projects p ON p.id = t.project_id
            LEFT JOIN time_entries te ON te.task_id = t.id
            WHERE t.project_id = ?
            GROUP BY t.id
            ORDER BY t.created_at DESC
            """,
            (project_id,),
        ).fetchall()
        return tasks

    def fetch_project(self, project_id):
        db = self._get_db()
        return db.execute(
            "SELECT id, name, created_at FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()

    def create_task(self, name, created_at, project_id):
        db = self._get_db()
        db.execute(
            "INSERT INTO tasks (name, created_at, project_id) VALUES (?, ?, ?)",
            (name, created_at, project_id),
        )
        db.commit()
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]

    def fetch_projects(self):
        db = self._get_db()
        return db.execute(
            "SELECT id, name, created_at FROM projects ORDER BY created_at DESC"
        ).fetchall()

    def create_project(self, name, created_at):
        db = self._get_db()
        db.execute(
            "INSERT INTO projects (name, created_at) VALUES (?, ?)",
            (name, created_at),
        )
        db.commit()
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]

    def delete_project(self, project_id):
        db = self._get_db()
        db.execute(
            """
            DELETE FROM time_entries
            WHERE task_id IN (SELECT id FROM tasks WHERE project_id = ?)
            """,
            (project_id,),
        )
        db.execute(
            "DELETE FROM task_labels WHERE task_id IN (SELECT id FROM tasks WHERE project_id = ?)",
            (project_id,),
        )
        db.execute("DELETE FROM project_labels WHERE project_id = ?", (project_id,))
        db.execute("DELETE FROM tasks WHERE project_id = ?", (project_id,))
        db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        db.commit()

    def fetch_labels(self):
        db = self._get_db()
        return db.execute(
            "SELECT id, name, color, created_at FROM labels ORDER BY created_at DESC"
        ).fetchall()

    def create_label(self, name, color, created_at):
        db = self._get_db()
        db.execute(
            "INSERT INTO labels (name, color, created_at) VALUES (?, ?, ?)",
            (name, color, created_at),
        )
        db.commit()

    def delete_label(self, label_id):
        db = self._get_db()
        db.execute("DELETE FROM task_labels WHERE label_id = ?", (label_id,))
        db.execute("DELETE FROM project_labels WHERE label_id = ?", (label_id,))
        db.execute("DELETE FROM labels WHERE id = ?", (label_id,))
        db.commit()

    def add_label_to_task(self, task_id, label_id):
        db = self._get_db()
        db.execute(
            "INSERT OR IGNORE INTO task_labels (task_id, label_id) VALUES (?, ?)",
            (task_id, label_id),
        )
        db.commit()

    def add_label_to_project(self, project_id, label_id):
        db = self._get_db()
        db.execute(
            "INSERT OR IGNORE INTO project_labels (project_id, label_id) VALUES (?, ?)",
            (project_id, label_id),
        )
        db.commit()

    def fetch_task_labels_map(self, task_ids):
        if not task_ids:
            return {}
        db = self._get_db()
        placeholders = ",".join(["?"] * len(task_ids))
        rows = db.execute(
            f"""
            SELECT tl.task_id, l.id, l.name, l.color
            FROM task_labels tl
            JOIN labels l ON l.id = tl.label_id
            WHERE tl.task_id IN ({placeholders})
            ORDER BY l.created_at DESC
            """,
            tuple(task_ids),
        ).fetchall()
        labels_map = {}
        for row in rows:
            labels_map.setdefault(row["task_id"], []).append(
                {"id": row["id"], "name": row["name"], "color": row["color"]}
            )
        return labels_map

    def fetch_project_labels_map(self, project_ids):
        if not project_ids:
            return {}
        db = self._get_db()
        placeholders = ",".join(["?"] * len(project_ids))
        rows = db.execute(
            f"""
            SELECT pl.project_id, l.id, l.name, l.color
            FROM project_labels pl
            JOIN labels l ON l.id = pl.label_id
            WHERE pl.project_id IN ({placeholders})
            ORDER BY l.created_at DESC
            """,
            tuple(project_ids),
        ).fetchall()
        labels_map = {}
        for row in rows:
            labels_map.setdefault(row["project_id"], []).append(
                {"id": row["id"], "name": row["name"], "color": row["color"]}
            )
        return labels_map

    def is_task_running(self, task_id):
        db = self._get_db()
        row = db.execute(
            "SELECT 1 FROM time_entries WHERE task_id = ? AND ended_at IS NULL",
            (task_id,),
        ).fetchone()
        return row is not None

    def start_task(self, task_id, started_at):
        db = self._get_db()
        db.execute(
            "INSERT INTO time_entries (task_id, started_at) VALUES (?, ?)",
            (task_id, started_at),
        )
        db.commit()

    def stop_task(self, task_id, ended_at):
        db = self._get_db()
        db.execute(
            """
            UPDATE time_entries
            SET ended_at = ?
            WHERE task_id = ? AND ended_at IS NULL
            """,
            (ended_at, task_id),
        )
        db.commit()

    def delete_task(self, task_id):
        db = self._get_db()
        db.execute("DELETE FROM time_entries WHERE task_id = ?", (task_id,))
        db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        db.commit()
