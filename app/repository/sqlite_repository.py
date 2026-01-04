import sqlite3
from datetime import datetime

from flask import g


class SQLiteTaskRepository:
    def __init__(self, db_path):
        self.db_path = db_path
        self.user_id = None

    def set_user_id(self, user_id):
        self.user_id = int(user_id) if user_id is not None else None

    def _require_user_id(self):
        if self.user_id is None:
            raise RuntimeError("User context not set for repository access.")
        return self.user_id

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
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (user_id, name),
                FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (user_id, name),
                FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
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
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                project_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
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
                user_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES tasks (id)
            );

            CREATE TABLE IF NOT EXISTS task_daily_checks (
                task_id INTEGER NOT NULL,
                log_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (task_id, log_date),
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                target_date TEXT,
                target_seconds INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS goal_projects (
                goal_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                PRIMARY KEY (goal_id, project_id),
                FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS goal_tasks (
                goal_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                PRIMARY KEY (goal_id, task_id),
                FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS goal_subgoals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                frequency TEXT NOT NULL,
                time_of_day TEXT,
                reminder TEXT,
                notes TEXT,
                goal_name TEXT,
                subgoal_name TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS habit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL,
                log_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (habit_id, log_date),
                FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        columns = db.execute("PRAGMA table_info(tasks)").fetchall()
        column_names = {column["name"] for column in columns}
        project_columns = db.execute("PRAGMA table_info(projects)").fetchall()
        project_names = {column["name"] for column in project_columns}
        if "user_id" not in project_names:
            db.execute("ALTER TABLE projects ADD COLUMN user_id INTEGER")
        label_columns = db.execute("PRAGMA table_info(labels)").fetchall()
        label_names = {column["name"] for column in label_columns}
        if "user_id" not in label_names:
            db.execute("ALTER TABLE labels ADD COLUMN user_id INTEGER")
        if "user_id" not in column_names:
            db.execute("ALTER TABLE tasks ADD COLUMN user_id INTEGER")
        if "project_id" not in column_names:
            db.execute("ALTER TABLE tasks ADD COLUMN project_id INTEGER")
        if "status" not in column_names:
            db.execute(
                "ALTER TABLE tasks ADD COLUMN status TEXT NOT NULL DEFAULT 'active'"
            )
        if "completed_at" not in column_names:
            db.execute("ALTER TABLE tasks ADD COLUMN completed_at TEXT")
        entry_columns = db.execute("PRAGMA table_info(time_entries)").fetchall()
        entry_names = {column["name"] for column in entry_columns}
        if "user_id" not in entry_names:
            db.execute("ALTER TABLE time_entries ADD COLUMN user_id INTEGER")
        goal_columns = db.execute("PRAGMA table_info(goals)").fetchall()
        goal_names = {column["name"] for column in goal_columns}
        if "user_id" not in goal_names:
            db.execute("ALTER TABLE goals ADD COLUMN user_id INTEGER")
        habit_columns = db.execute("PRAGMA table_info(habits)").fetchall()
        habit_names = {column["name"] for column in habit_columns}
        if "user_id" not in habit_names:
            db.execute("ALTER TABLE habits ADD COLUMN user_id INTEGER")
        if "goal_name" not in habit_names:
            db.execute("ALTER TABLE habits ADD COLUMN goal_name TEXT")
        if "subgoal_name" not in habit_names:
            db.execute("ALTER TABLE habits ADD COLUMN subgoal_name TEXT")
        default_user = db.execute(
            "SELECT id FROM user ORDER BY id ASC LIMIT 1"
        ).fetchone()
        if default_user:
            default_user_id = default_user["id"]
            db.execute(
                "UPDATE projects SET user_id = ? WHERE user_id IS NULL",
                (default_user_id,),
            )
            db.execute(
                "UPDATE labels SET user_id = ? WHERE user_id IS NULL",
                (default_user_id,),
            )
            db.execute(
                "UPDATE tasks SET user_id = ? WHERE user_id IS NULL",
                (default_user_id,),
            )
            db.execute(
                "UPDATE time_entries SET user_id = ? WHERE user_id IS NULL",
                (default_user_id,),
            )
            db.execute(
                "UPDATE goals SET user_id = ? WHERE user_id IS NULL",
                (default_user_id,),
            )
            db.execute(
                "UPDATE habits SET user_id = ? WHERE user_id IS NULL",
                (default_user_id,),
            )
        db.commit()

    def ensure_default_project(self, name, created_at):
        db = self._get_db()
        if self.user_id is None:
            return None
        user_id = self.user_id
        db.execute(
            """
            INSERT OR IGNORE INTO projects (user_id, name, created_at)
            VALUES (?, ?, ?)
            """,
            (user_id, name, created_at),
        )
        row = db.execute(
            "SELECT id FROM projects WHERE user_id = ? AND name = ?",
            (user_id, name),
        ).fetchone()
        return row["id"] if row else None

    def backfill_tasks_project(self, project_id):
        db = self._get_db()
        if self.user_id is None:
            return
        user_id = self.user_id
        db.execute(
            "UPDATE tasks SET project_id = ? WHERE user_id = ? AND (project_id IS NULL OR project_id = 0)",
            (project_id, user_id),
        )
        db.commit()

    def fetch_tasks(self, now_ts=None, rolling_start=None, day_start=None):
        db = self._get_db()
        user_id = self._require_user_id()
        now_ts = int(now_ts or datetime.utcnow().timestamp())
        rolling_start = int(rolling_start or (now_ts - 24 * 60 * 60))
        day_start = int(
            day_start
            or datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        )
        tasks = db.execute(
            """
            WITH params AS (
                SELECT
                    ? AS now_ts,
                    ? AS rolling_start,
                    ? AS day_start
            )
            SELECT t.id, t.name, t.project_id, t.status, t.completed_at,
                   p.name AS project_name,
                   IFNULL(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           WHEN te.ended_at IS NULL THEN (params.now_ts - strftime('%s', te.started_at, 'utc'))
                           ELSE (strftime('%s', te.ended_at, 'utc') - strftime('%s', te.started_at, 'utc'))
                       END
                   ), 0) AS total_seconds,
                   IFNULL(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           ELSE MAX(
                               0,
                               MIN(
                                   COALESCE(CAST(strftime('%s', te.ended_at, 'utc') AS INTEGER), params.now_ts),
                                   params.now_ts
                               ) - MAX(CAST(strftime('%s', te.started_at, 'utc') AS INTEGER), params.rolling_start)
                           )
                       END
                   ), 0) AS rolling_24h_seconds,
                   IFNULL(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           ELSE MAX(
                               0,
                               MIN(
                                   COALESCE(CAST(strftime('%s', te.ended_at, 'utc') AS INTEGER), params.now_ts),
                                   params.now_ts
                               ) - MAX(CAST(strftime('%s', te.started_at, 'utc') AS INTEGER), params.day_start)
                           )
                       END
                   ), 0) AS today_seconds,
                   MAX(CASE WHEN te.id IS NOT NULL AND te.ended_at IS NULL THEN 1 ELSE 0 END) AS is_running
            FROM tasks t
            CROSS JOIN params
            LEFT JOIN projects p ON p.id = t.project_id
            LEFT JOIN time_entries te ON te.task_id = t.id AND te.user_id = ?
            WHERE t.user_id = ?
            GROUP BY t.id
            ORDER BY t.created_at DESC
            """,
            (now_ts, rolling_start, day_start, user_id, user_id),
        ).fetchall()
        return tasks

    def fetch_tasks_by_project(self, project_id, now_ts=None, rolling_start=None, day_start=None):
        db = self._get_db()
        user_id = self._require_user_id()
        now_ts = int(now_ts or datetime.utcnow().timestamp())
        rolling_start = int(rolling_start or (now_ts - 24 * 60 * 60))
        day_start = int(
            day_start
            or datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        )
        tasks = db.execute(
            """
            WITH params AS (
                SELECT
                    ? AS now_ts,
                    ? AS rolling_start,
                    ? AS day_start
            )
            SELECT t.id, t.name, t.project_id, t.status, t.completed_at,
                   p.name AS project_name,
                   IFNULL(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           WHEN te.ended_at IS NULL THEN (params.now_ts - strftime('%s', te.started_at, 'utc'))
                           ELSE (strftime('%s', te.ended_at, 'utc') - strftime('%s', te.started_at, 'utc'))
                       END
                   ), 0) AS total_seconds,
                   IFNULL(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           ELSE MAX(
                               0,
                               MIN(
                                   COALESCE(CAST(strftime('%s', te.ended_at, 'utc') AS INTEGER), params.now_ts),
                                   params.now_ts
                               ) - MAX(CAST(strftime('%s', te.started_at, 'utc') AS INTEGER), params.rolling_start)
                           )
                       END
                   ), 0) AS rolling_24h_seconds,
                   IFNULL(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           ELSE MAX(
                               0,
                               MIN(
                                   COALESCE(CAST(strftime('%s', te.ended_at, 'utc') AS INTEGER), params.now_ts),
                                   params.now_ts
                               ) - MAX(CAST(strftime('%s', te.started_at, 'utc') AS INTEGER), params.day_start)
                           )
                       END
                   ), 0) AS today_seconds,
                   MAX(CASE WHEN te.id IS NOT NULL AND te.ended_at IS NULL THEN 1 ELSE 0 END) AS is_running
            FROM tasks t
            CROSS JOIN params
            LEFT JOIN projects p ON p.id = t.project_id
            LEFT JOIN time_entries te ON te.task_id = t.id AND te.user_id = ?
            WHERE t.user_id = ? AND t.project_id = ?
            GROUP BY t.id
            ORDER BY t.created_at DESC
            """,
            (now_ts, rolling_start, day_start, user_id, user_id, project_id),
        ).fetchall()
        return tasks

    def fetch_project(self, project_id):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            "SELECT id, name, created_at FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user_id),
        ).fetchone()

    def create_task(self, name, created_at, project_id):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            INSERT INTO tasks (user_id, name, created_at, project_id)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, name, created_at, project_id),
        )
        db.commit()
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_task(self, task_id, name):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "UPDATE tasks SET name = ? WHERE id = ? AND user_id = ?",
            (name, task_id, user_id),
        )
        db.commit()

    def set_task_status(self, task_id, status, completed_at):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ? AND user_id = ?",
            (status, completed_at, task_id, user_id),
        )
        db.commit()

    def fetch_projects(self):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            "SELECT id, name, created_at FROM projects WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()

    def fetch_projects_by_ids(self, project_ids):
        if not project_ids:
            return []
        db = self._get_db()
        user_id = self._require_user_id()
        placeholders = ",".join(["?"] * len(project_ids))
        return db.execute(
            f"""
            SELECT id, name, created_at
            FROM projects
            WHERE user_id = ? AND id IN ({placeholders})
            """,
            (user_id, *project_ids),
        ).fetchall()

    def create_project(self, name, created_at):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "INSERT INTO projects (user_id, name, created_at) VALUES (?, ?, ?)",
            (user_id, name, created_at),
        )
        db.commit()
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_project(self, project_id, name):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "UPDATE projects SET name = ? WHERE id = ? AND user_id = ?",
            (name, project_id, user_id),
        )
        db.commit()

    def delete_project(self, project_id):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            DELETE FROM time_entries
            WHERE user_id = ? AND task_id IN (
                SELECT id FROM tasks WHERE project_id = ? AND user_id = ?
            )
            """,
            (user_id, project_id, user_id),
        )
        db.execute(
            """
            DELETE FROM task_labels
            WHERE task_id IN (
                SELECT id FROM tasks WHERE project_id = ? AND user_id = ?
            )
            """,
            (project_id, user_id),
        )
        db.execute(
            "DELETE FROM project_labels WHERE project_id = ?",
            (project_id,),
        )
        db.execute("DELETE FROM tasks WHERE project_id = ? AND user_id = ?", (project_id, user_id))
        db.execute("DELETE FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id))
        db.commit()

    def fetch_labels(self):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT id, name, color, created_at
            FROM labels
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()

    def fetch_tasks_by_project_ids(self, project_ids):
        if not project_ids:
            return []
        db = self._get_db()
        user_id = self._require_user_id()
        placeholders = ",".join(["?"] * len(project_ids))
        return db.execute(
            f"""
            SELECT id, name, created_at, project_id
            FROM tasks
            WHERE user_id = ? AND project_id IN ({placeholders})
            """,
            (user_id, *project_ids),
        ).fetchall()

    def fetch_task_total_seconds(self, task_ids):
        if not task_ids:
            return {}
        db = self._get_db()
        user_id = self._require_user_id()
        placeholders = ",".join(["?"] * len(task_ids))
        rows = db.execute(
            f"""
            SELECT t.id AS task_id,
                   IFNULL(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           WHEN te.ended_at IS NULL THEN (strftime('%s','now') - strftime('%s', te.started_at))
                           ELSE (strftime('%s', te.ended_at) - strftime('%s', te.started_at))
                       END
                   ), 0) AS total_seconds
            FROM tasks t
            LEFT JOIN time_entries te ON te.task_id = t.id AND te.user_id = ?
            WHERE t.user_id = ? AND t.id IN ({placeholders})
            GROUP BY t.id
            """,
            (user_id, user_id, *task_ids),
        ).fetchall()
        return {row["task_id"]: int(row["total_seconds"] or 0) for row in rows}

    def get_setting(self, key):
        db = self._get_db()
        user_id = self.user_id
        scoped_key = f"user:{user_id}:{key}" if user_id is not None else key
        row = db.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (scoped_key,),
        ).fetchone()
        if row:
            return row["value"]
        if user_id is None:
            return None
        fallback = db.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (key,),
        ).fetchone()
        return fallback["value"] if fallback else None

    def set_setting(self, key, value):
        db = self._get_db()
        user_id = self.user_id
        scoped_key = f"user:{user_id}:{key}" if user_id is not None else key
        db.execute(
            """
            INSERT INTO app_settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (scoped_key, value),
        )
        db.commit()

    def create_label(self, name, color, created_at):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "INSERT INTO labels (user_id, name, color, created_at) VALUES (?, ?, ?, ?)",
            (user_id, name, color, created_at),
        )
        db.commit()

    def update_label(self, label_id, name, color):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "UPDATE labels SET name = ?, color = ? WHERE id = ? AND user_id = ?",
            (name, color, label_id, user_id),
        )
        db.commit()

    def delete_label(self, label_id):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute("DELETE FROM task_labels WHERE label_id = ?", (label_id,))
        db.execute("DELETE FROM project_labels WHERE label_id = ?", (label_id,))
        db.execute("DELETE FROM labels WHERE id = ? AND user_id = ?", (label_id, user_id))
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

    def fetch_goals(self):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT id, name, description, status, priority, target_date, target_seconds, created_at
            FROM goals
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()

    def fetch_goal(self, goal_id):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT id, name, description, status, priority, target_date, target_seconds, created_at
            FROM goals
            WHERE id = ? AND user_id = ?
            """,
            (goal_id, user_id),
        ).fetchone()

    def create_goal(self, name, description, status, priority, target_date, target_seconds, created_at):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            INSERT INTO goals (user_id, name, description, status, priority, target_date, target_seconds, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, name, description, status, priority, target_date, target_seconds, created_at),
        )
        db.commit()
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_goal(self, goal_id, name, description, status, priority, target_date, target_seconds):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            UPDATE goals
            SET name = ?, description = ?, status = ?, priority = ?, target_date = ?, target_seconds = ?
            WHERE id = ? AND user_id = ?
            """,
            (name, description, status, priority, target_date, target_seconds, goal_id, user_id),
        )
        db.commit()

    def delete_goal(self, goal_id):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            DELETE FROM goal_tasks
            WHERE goal_id IN (SELECT id FROM goals WHERE id = ? AND user_id = ?)
            """,
            (goal_id, user_id),
        )
        db.execute(
            """
            DELETE FROM goal_projects
            WHERE goal_id IN (SELECT id FROM goals WHERE id = ? AND user_id = ?)
            """,
            (goal_id, user_id),
        )
        db.execute(
            """
            DELETE FROM goal_subgoals
            WHERE goal_id IN (SELECT id FROM goals WHERE id = ? AND user_id = ?)
            """,
            (goal_id, user_id),
        )
        db.execute("DELETE FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
        db.commit()

    def fetch_goal_projects(self, goal_ids):
        if not goal_ids:
            return {}
        db = self._get_db()
        user_id = self._require_user_id()
        placeholders = ",".join(["?"] * len(goal_ids))
        rows = db.execute(
            f"""
            SELECT gp.goal_id, gp.project_id
            FROM goal_projects gp
            JOIN goals g ON g.id = gp.goal_id
            WHERE g.user_id = ? AND gp.goal_id IN ({placeholders})
            """,
            (user_id, *goal_ids),
        ).fetchall()
        mapping = {}
        for row in rows:
            mapping.setdefault(row["goal_id"], []).append(row["project_id"])
        return mapping

    def fetch_goal_tasks(self, goal_ids):
        if not goal_ids:
            return {}
        db = self._get_db()
        user_id = self._require_user_id()
        placeholders = ",".join(["?"] * len(goal_ids))
        rows = db.execute(
            f"""
            SELECT gt.goal_id, gt.task_id
            FROM goal_tasks gt
            JOIN goals g ON g.id = gt.goal_id
            WHERE g.user_id = ? AND gt.goal_id IN ({placeholders})
            """,
            (user_id, *goal_ids),
        ).fetchall()
        mapping = {}
        for row in rows:
            mapping.setdefault(row["goal_id"], []).append(row["task_id"])
        return mapping

    def fetch_goal_subgoals(self, goal_ids):
        if not goal_ids:
            return {}
        db = self._get_db()
        user_id = self._require_user_id()
        placeholders = ",".join(["?"] * len(goal_ids))
        rows = db.execute(
            f"""
            SELECT gs.id, gs.goal_id, gs.title, gs.status, gs.created_at
            FROM goal_subgoals gs
            JOIN goals g ON g.id = gs.goal_id
            WHERE g.user_id = ? AND gs.goal_id IN ({placeholders})
            ORDER BY gs.created_at ASC
            """,
            (user_id, *goal_ids),
        ).fetchall()
        mapping = {}
        for row in rows:
            mapping.setdefault(row["goal_id"], []).append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                }
            )
        return mapping

    def set_goal_projects(self, goal_id, project_ids):
        db = self._get_db()
        user_id = self._require_user_id()
        owns_goal = db.execute(
            "SELECT 1 FROM goals WHERE id = ? AND user_id = ?",
            (goal_id, user_id),
        ).fetchone()
        if not owns_goal:
            return
        db.execute("DELETE FROM goal_projects WHERE goal_id = ?", (goal_id,))
        for project_id in project_ids:
            db.execute(
                "INSERT OR IGNORE INTO goal_projects (goal_id, project_id) VALUES (?, ?)",
                (goal_id, project_id),
            )
        db.commit()

    def set_goal_tasks(self, goal_id, task_ids):
        db = self._get_db()
        user_id = self._require_user_id()
        owns_goal = db.execute(
            "SELECT 1 FROM goals WHERE id = ? AND user_id = ?",
            (goal_id, user_id),
        ).fetchone()
        if not owns_goal:
            return
        db.execute("DELETE FROM goal_tasks WHERE goal_id = ?", (goal_id,))
        for task_id in task_ids:
            db.execute(
                "INSERT OR IGNORE INTO goal_tasks (goal_id, task_id) VALUES (?, ?)",
                (goal_id, task_id),
            )
        db.commit()

    def set_goal_subgoals(self, goal_id, subgoal_titles, created_at):
        db = self._get_db()
        user_id = self._require_user_id()
        owns_goal = db.execute(
            "SELECT 1 FROM goals WHERE id = ? AND user_id = ?",
            (goal_id, user_id),
        ).fetchone()
        if not owns_goal:
            return
        db.execute("DELETE FROM goal_subgoals WHERE goal_id = ?", (goal_id,))
        for title in subgoal_titles:
            db.execute(
                """
                INSERT INTO goal_subgoals (goal_id, title, status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (goal_id, title, "pending", created_at),
            )
        db.commit()

    def fetch_goal_subgoal(self, subgoal_id):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT gs.id, gs.goal_id, gs.title, gs.status, gs.created_at
            FROM goal_subgoals gs
            JOIN goals g ON g.id = gs.goal_id
            WHERE gs.id = ? AND g.user_id = ?
            """,
            (subgoal_id, user_id),
        ).fetchone()

    def set_goal_subgoal_status(self, subgoal_id, status):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            UPDATE goal_subgoals
            SET status = ?
            WHERE id = ?
              AND goal_id IN (SELECT id FROM goals WHERE user_id = ?)
            """,
            (status, subgoal_id, user_id),
        )
        db.commit()

    def add_goal_subgoal(self, goal_id, title, created_at):
        db = self._get_db()
        user_id = self._require_user_id()
        owns_goal = db.execute(
            "SELECT 1 FROM goals WHERE id = ? AND user_id = ?",
            (goal_id, user_id),
        ).fetchone()
        if not owns_goal:
            return
        db.execute(
            """
            INSERT INTO goal_subgoals (goal_id, title, status, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (goal_id, title, "pending", created_at),
        )
        db.commit()

    def fetch_habits(self):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT id, name, frequency, time_of_day, reminder, notes, goal_name, subgoal_name, created_at
            FROM habits
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()

    def create_habit(
        self,
        name,
        frequency,
        time_of_day,
        reminder,
        notes,
        goal_name,
        subgoal_name,
        created_at,
    ):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            INSERT INTO habits (
                user_id, name, frequency, time_of_day, reminder, notes, goal_name, subgoal_name, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                name,
                frequency,
                time_of_day,
                reminder,
                notes,
                goal_name,
                subgoal_name,
                created_at,
            ),
        )
        db.commit()
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]

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
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            UPDATE habits
            SET name = ?, frequency = ?, time_of_day = ?, reminder = ?, notes = ?, goal_name = ?, subgoal_name = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                name,
                frequency,
                time_of_day,
                reminder,
                notes,
                goal_name,
                subgoal_name,
                habit_id,
                user_id,
            ),
        )
        db.commit()

    def delete_habit(self, habit_id):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "DELETE FROM habit_logs WHERE habit_id IN (SELECT id FROM habits WHERE id = ? AND user_id = ?)",
            (habit_id, user_id),
        )
        db.execute("DELETE FROM habits WHERE id = ? AND user_id = ?", (habit_id, user_id))
        db.commit()

    def fetch_habit_logs_for_date(self, habit_ids, log_date):
        if not habit_ids:
            return set()
        db = self._get_db()
        placeholders = ",".join(["?"] * len(habit_ids))
        rows = db.execute(
            f"""
            SELECT habit_id
            FROM habit_logs
            WHERE habit_id IN ({placeholders}) AND log_date = ?
            """,
            tuple(habit_ids) + (log_date,),
        ).fetchall()
        return {row["habit_id"] for row in rows}

    def fetch_habit_logs_map(self, habit_ids):
        if not habit_ids:
            return {}
        db = self._get_db()
        placeholders = ",".join(["?"] * len(habit_ids))
        rows = db.execute(
            f"""
            SELECT habit_id, log_date
            FROM habit_logs
            WHERE habit_id IN ({placeholders})
            ORDER BY log_date DESC
            """,
            tuple(habit_ids),
        ).fetchall()
        mapping = {}
        for row in rows:
            mapping.setdefault(row["habit_id"], set()).add(row["log_date"])
        return mapping

    def set_habit_log(self, habit_id, log_date, done):
        db = self._get_db()
        if done:
            db.execute(
                """
                INSERT OR IGNORE INTO habit_logs (habit_id, log_date, created_at)
                VALUES (?, ?, ?)
                """,
                (habit_id, log_date, datetime.utcnow().isoformat()),
            )
        else:
            db.execute(
                "DELETE FROM habit_logs WHERE habit_id = ? AND log_date = ?",
                (habit_id, log_date),
            )
        db.commit()

    def fetch_habit_log_counts(self, start_date, end_date):
        db = self._get_db()
        user_id = self._require_user_id()
        rows = db.execute(
            """
            SELECT log_date, COUNT(*) AS total
            FROM habit_logs
            WHERE habit_id IN (SELECT id FROM habits WHERE user_id = ?)
              AND log_date BETWEEN ? AND ?
            GROUP BY log_date
            ORDER BY log_date ASC
            """,
            (user_id, start_date, end_date),
        ).fetchall()
        return {row["log_date"]: row["total"] for row in rows}

    def fetch_task_labels_map(self, task_ids):
        if not task_ids:
            return {}
        db = self._get_db()
        user_id = self._require_user_id()
        placeholders = ",".join(["?"] * len(task_ids))
        rows = db.execute(
            f"""
            SELECT tl.task_id, l.id, l.name, l.color
            FROM task_labels tl
            JOIN labels l ON l.id = tl.label_id
            JOIN tasks t ON t.id = tl.task_id
            WHERE t.user_id = ? AND l.user_id = ? AND tl.task_id IN ({placeholders})
            ORDER BY l.created_at DESC
            """,
            (user_id, user_id, *task_ids),
        ).fetchall()
        labels_map = {}
        for row in rows:
            labels_map.setdefault(row["task_id"], []).append(
                {"id": row["id"], "name": row["name"], "color": row["color"]}
            )
        return labels_map

    def fetch_task_daily_checks_for_date(self, task_ids, log_date):
        if not task_ids:
            return set()
        db = self._get_db()
        placeholders = ",".join(["?"] * len(task_ids))
        rows = db.execute(
            f"""
            SELECT task_id
            FROM task_daily_checks
            WHERE task_id IN ({placeholders}) AND log_date = ?
            """,
            tuple(task_ids) + (log_date,),
        ).fetchall()
        return {row["task_id"] for row in rows}

    def fetch_task_daily_check_counts(self, task_ids):
        if not task_ids:
            return {}
        db = self._get_db()
        placeholders = ",".join(["?"] * len(task_ids))
        rows = db.execute(
            f"""
            SELECT task_id, COUNT(*) AS total
            FROM task_daily_checks
            WHERE task_id IN ({placeholders})
            GROUP BY task_id
            """,
            tuple(task_ids),
        ).fetchall()
        return {row["task_id"]: row["total"] for row in rows}

    def set_task_daily_check(self, task_id, log_date, done):
        db = self._get_db()
        if done:
            db.execute(
                """
                INSERT OR IGNORE INTO task_daily_checks (task_id, log_date, created_at)
                VALUES (?, ?, ?)
                """,
                (task_id, log_date, datetime.utcnow().isoformat()),
            )
        else:
            db.execute(
                "DELETE FROM task_daily_checks WHERE task_id = ? AND log_date = ?",
                (task_id, log_date),
            )
        db.commit()

    def fetch_project_labels_map(self, project_ids):
        if not project_ids:
            return {}
        db = self._get_db()
        user_id = self._require_user_id()
        placeholders = ",".join(["?"] * len(project_ids))
        rows = db.execute(
            f"""
            SELECT pl.project_id, l.id, l.name, l.color
            FROM project_labels pl
            JOIN labels l ON l.id = pl.label_id
            JOIN projects p ON p.id = pl.project_id
            WHERE p.user_id = ? AND l.user_id = ? AND pl.project_id IN ({placeholders})
            ORDER BY l.created_at DESC
            """,
            (user_id, user_id, *project_ids),
        ).fetchall()
        labels_map = {}
        for row in rows:
            labels_map.setdefault(row["project_id"], []).append(
                {"id": row["id"], "name": row["name"], "color": row["color"]}
            )
        return labels_map

    def is_task_running(self, task_id):
        db = self._get_db()
        user_id = self._require_user_id()
        row = db.execute(
            """
            SELECT 1
            FROM time_entries
            WHERE task_id = ? AND ended_at IS NULL AND user_id = ?
            """,
            (task_id, user_id),
        ).fetchone()
        return row is not None

    def start_task(self, task_id, started_at):
        db = self._get_db()
        user_id = self._require_user_id()
        owns_task = db.execute(
            "SELECT 1 FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        ).fetchone()
        if not owns_task:
            return
        db.execute(
            "INSERT INTO time_entries (user_id, task_id, started_at) VALUES (?, ?, ?)",
            (user_id, task_id, started_at),
        )
        db.commit()

    def stop_task(self, task_id, ended_at):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            UPDATE time_entries
            SET ended_at = ?
            WHERE task_id = ? AND ended_at IS NULL AND user_id = ?
            """,
            (ended_at, task_id, user_id),
        )
        db.commit()

    def fetch_running_time_entries(self):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT id, task_id, started_at
            FROM time_entries
            WHERE ended_at IS NULL AND user_id = ?
            """,
            (user_id,),
        ).fetchall()

    def stop_time_entry(self, entry_id, ended_at):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            UPDATE time_entries
            SET ended_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (ended_at, entry_id, user_id),
        )
        db.commit()

    def delete_task(self, task_id):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "DELETE FROM time_entries WHERE task_id = ? AND user_id = ?",
            (task_id, user_id),
        )
        db.execute("DELETE FROM task_labels WHERE task_id = ?", (task_id,))
        db.execute("DELETE FROM task_daily_checks WHERE task_id = ?", (task_id,))
        db.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
        db.commit()

    def fetch_time_entries_between(self, start_iso, end_iso):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT id, task_id, started_at, ended_at
            FROM time_entries
            WHERE user_id = ?
              AND started_at < ?
              AND (ended_at IS NULL OR ended_at > ?)
            """,
            (user_id, end_iso, start_iso),
        ).fetchall()

    def fetch_time_entries_with_projects_between(self, start_iso, end_iso):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT te.id, te.task_id, te.started_at, te.ended_at,
                   t.project_id, p.name AS project_name
            FROM time_entries te
            JOIN tasks t ON t.id = te.task_id
            LEFT JOIN projects p ON p.id = t.project_id
            WHERE te.user_id = ?
              AND t.user_id = ?
              AND te.started_at < ?
              AND (te.ended_at IS NULL OR te.ended_at > ?)
            """,
            (user_id, user_id, end_iso, start_iso),
        ).fetchall()

    def fetch_time_entries_with_tasks_between(self, start_iso, end_iso):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT te.id, te.task_id, te.started_at, te.ended_at,
                   t.name AS task_name
            FROM time_entries te
            JOIN tasks t ON t.id = te.task_id
            WHERE te.user_id = ?
              AND t.user_id = ?
              AND te.started_at < ?
              AND (te.ended_at IS NULL OR te.ended_at > ?)
            """,
            (user_id, user_id, end_iso, start_iso),
        ).fetchall()

    def fetch_time_entries_with_labels_between(self, start_iso, end_iso):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT te.id, te.task_id, te.started_at, te.ended_at,
                   l.name AS label_name
            FROM time_entries te
            JOIN task_labels tl ON tl.task_id = te.task_id
            JOIN labels l ON l.id = tl.label_id
            WHERE te.user_id = ?
              AND l.user_id = ?
              AND te.started_at < ?
              AND (te.ended_at IS NULL OR te.ended_at > ?)
            """,
            (user_id, user_id, end_iso, start_iso),
        ).fetchall()

    def fetch_time_entries_with_task_details_between(self, start_iso, end_iso):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT te.id, te.task_id, te.started_at, te.ended_at,
                   t.name AS task_name, p.name AS project_name
            FROM time_entries te
            JOIN tasks t ON t.id = te.task_id
            LEFT JOIN projects p ON p.id = t.project_id
            WHERE te.user_id = ?
              AND t.user_id = ?
              AND te.started_at < ?
              AND (te.ended_at IS NULL OR te.ended_at > ?)
            ORDER BY te.started_at DESC
            """,
            (user_id, user_id, end_iso, start_iso),
        ).fetchall()
