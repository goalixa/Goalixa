import sqlite3

from flask import g


class SQLiteTaskRepository:
    def __init__(self, db_path):
        self.db_path = db_path

    def _get_db(self):
        if "db" not in g:
            g.db = sqlite3.connect(self.db_path)
            g.db.row_factory = sqlite3.Row
        return g.db

    def close_db(self, exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db(self):
        db = self._get_db()
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

    def fetch_tasks(self):
        db = self._get_db()
        tasks = db.execute(
            """
            SELECT t.id, t.name,
                   IFNULL(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           WHEN te.ended_at IS NULL THEN (strftime('%s','now') - strftime('%s', te.started_at))
                           ELSE (strftime('%s', te.ended_at) - strftime('%s', te.started_at))
                       END
                   ), 0) AS total_seconds,
                   MAX(CASE WHEN te.id IS NOT NULL AND te.ended_at IS NULL THEN 1 ELSE 0 END) AS is_running
            FROM tasks t
            LEFT JOIN time_entries te ON te.task_id = t.id
            GROUP BY t.id
            ORDER BY t.created_at DESC
            """
        ).fetchall()
        return tasks

    def create_task(self, name, created_at):
        db = self._get_db()
        db.execute(
            "INSERT INTO tasks (name, created_at) VALUES (?, ?)",
            (name, created_at),
        )
        db.commit()

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
