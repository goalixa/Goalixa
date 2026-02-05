import psycopg
from psycopg.rows import dict_row
from datetime import datetime

from flask import g


class PostgresTaskRepository:
    def __init__(self, database_url):
        self.database_url = database_url
        self.user_id = None

    def set_user_id(self, user_id):
        self.user_id = int(user_id) if user_id is not None else None

    def _require_user_id(self):
        if self.user_id is None:
            raise RuntimeError("User context not set for repository access.")
        return self.user_id

    def _get_db(self):
        if "db" not in g:
            g.db = psycopg.connect(self.database_url, row_factory=dict_row)
        return g.db

    def close_db(self, exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db(self):
        db = self._get_db()
        statements = [
            """
            CREATE TABLE IF NOT EXISTS "user" (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (user_id, name),
                FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS labels (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (user_id, name),
                FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS project_labels (
                project_id INTEGER NOT NULL,
                label_id INTEGER NOT NULL,
                PRIMARY KEY (project_id, label_id),
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (label_id) REFERENCES labels (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                project_id INTEGER,
                status TEXT NOT NULL DEFAULT 'active',
                completed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS task_labels (
                task_id INTEGER NOT NULL,
                label_id INTEGER NOT NULL,
                PRIMARY KEY (task_id, label_id),
                FOREIGN KEY (task_id) REFERENCES tasks (id),
                FOREIGN KEY (label_id) REFERENCES labels (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS time_entries (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES tasks (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS task_daily_checks (
                task_id INTEGER NOT NULL,
                log_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (task_id, log_date),
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS goals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                target_date TEXT,
                target_seconds INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS goal_projects (
                goal_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                PRIMARY KEY (goal_id, project_id),
                FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS goal_tasks (
                goal_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                PRIMARY KEY (goal_id, task_id),
                FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS goal_subgoals (
                id SERIAL PRIMARY KEY,
                goal_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                label TEXT,
                target_date TEXT,
                project_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE SET NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS habits (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                frequency TEXT NOT NULL,
                time_of_day TEXT,
                reminder TEXT,
                notes TEXT,
                goal_name TEXT,
                subgoal_name TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS habit_logs (
                id SERIAL PRIMARY KEY,
                habit_id INTEGER NOT NULL,
                log_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (habit_id, log_date),
                FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                notes TEXT,
                remind_date TEXT,
                remind_time TEXT,
                repeat_interval TEXT NOT NULL DEFAULT 'none',
                repeat_days TEXT,
                priority TEXT NOT NULL DEFAULT 'normal',
                channel_toast INTEGER NOT NULL DEFAULT 1,
                channel_system INTEGER NOT NULL DEFAULT 0,
                play_sound INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS daily_todos (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                log_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS weekly_goals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                target_seconds INTEGER NOT NULL DEFAULT 0,
                week_start TEXT NOT NULL,
                week_end TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """,
        ]
        for statement in statements:
            db.execute(statement)

        db.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS user_id INTEGER")
        db.execute("ALTER TABLE labels ADD COLUMN IF NOT EXISTS user_id INTEGER")
        db.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS user_id INTEGER")
        db.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS project_id INTEGER")
        db.execute(
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active'"
        )
        db.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completed_at TEXT")
        db.execute("ALTER TABLE time_entries ADD COLUMN IF NOT EXISTS user_id INTEGER")
        db.execute("ALTER TABLE goals ADD COLUMN IF NOT EXISTS user_id INTEGER")
        db.execute("ALTER TABLE goal_subgoals ADD COLUMN IF NOT EXISTS label TEXT")
        db.execute("ALTER TABLE goal_subgoals ADD COLUMN IF NOT EXISTS target_date TEXT")
        db.execute("ALTER TABLE goal_subgoals ADD COLUMN IF NOT EXISTS project_id INTEGER")
        db.execute("ALTER TABLE habits ADD COLUMN IF NOT EXISTS user_id INTEGER")
        db.execute("ALTER TABLE habits ADD COLUMN IF NOT EXISTS goal_name TEXT")
        db.execute("ALTER TABLE habits ADD COLUMN IF NOT EXISTS subgoal_name TEXT")
        db.execute("ALTER TABLE weekly_goals ADD COLUMN IF NOT EXISTS user_id INTEGER")

        default_user = db.execute(
            'SELECT id FROM "user" ORDER BY id ASC LIMIT 1'
        ).fetchone()
        if default_user:
            default_user_id = default_user["id"]
            db.execute(
                "UPDATE projects SET user_id = %s WHERE user_id IS NULL",
                (default_user_id,),
            )
            db.execute(
                "UPDATE labels SET user_id = %s WHERE user_id IS NULL",
                (default_user_id,),
            )
            db.execute(
                "UPDATE tasks SET user_id = %s WHERE user_id IS NULL",
                (default_user_id,),
            )
            db.execute(
                "UPDATE time_entries SET user_id = %s WHERE user_id IS NULL",
                (default_user_id,),
            )
            db.execute(
                "UPDATE goals SET user_id = %s WHERE user_id IS NULL",
                (default_user_id,),
            )
            db.execute(
                "UPDATE habits SET user_id = %s WHERE user_id IS NULL",
                (default_user_id,),
            )
            db.execute(
                "UPDATE weekly_goals SET user_id = %s WHERE user_id IS NULL",
                (default_user_id,),
            )
        db.commit()

    def fetch_weekly_goals(self, week_start=None, week_end=None):
        user_id = self._require_user_id()
        db = self._get_db()
        if week_start and week_end:
            rows = db.execute(
                """
                SELECT id, title, target_seconds, week_start, week_end, status, created_at
                FROM weekly_goals
                WHERE user_id = %s AND week_start = %s AND week_end = %s
                ORDER BY created_at DESC
                """,
                (user_id, week_start, week_end),
            ).fetchall()
        else:
            rows = db.execute(
                """
                SELECT id, title, target_seconds, week_start, week_end, status, created_at
                FROM weekly_goals
                WHERE user_id = %s
                ORDER BY week_start DESC, created_at DESC
                """,
                (user_id,),
            ).fetchall()
        return rows

    def create_weekly_goal(
        self, title, target_seconds, week_start, week_end, status, created_at
    ):
        user_id = self._require_user_id()
        db = self._get_db()
        cursor = db.execute(
            """
            INSERT INTO weekly_goals
                (user_id, title, target_seconds, week_start, week_end, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                title,
                int(target_seconds or 0),
                week_start,
                week_end,
                status,
                created_at,
            ),
        )
        row = cursor.fetchone()
        db.commit()
        return row["id"] if row else None

    def update_weekly_goal(self, goal_id, title, target_seconds, status):
        user_id = self._require_user_id()
        db = self._get_db()
        db.execute(
            """
            UPDATE weekly_goals
            SET title = %s, target_seconds = %s, status = %s
            WHERE id = %s AND user_id = %s
            """,
            (title, int(target_seconds or 0), status, int(goal_id), user_id),
        )
        db.commit()

    def delete_weekly_goal(self, goal_id):
        user_id = self._require_user_id()
        db = self._get_db()
        db.execute(
            "DELETE FROM weekly_goals WHERE id = %s AND user_id = %s",
            (int(goal_id), user_id),
        )
        db.commit()

    def ensure_user(self, email):
        """Ensure user exists in the database. Create if not exists."""
        if self.user_id is None:
            return None
        db = self._get_db()
        user_id = self.user_id

        # Check if user exists
        row = db.execute('SELECT id FROM "user" WHERE id = %s', (user_id,)).fetchone()
        if row:
            return user_id

        # Create user with their email
        db.execute(
            'INSERT INTO "user" (id, email, created_at) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING',
            (user_id, email, datetime.utcnow().isoformat()),
        )
        db.commit()
        return user_id

    def ensure_default_project(self, name, created_at):
        db = self._get_db()
        if self.user_id is None:
            return None
        user_id = self.user_id
        db.execute(
            """
            INSERT INTO projects (user_id, name, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, name) DO NOTHING
            """,
            (user_id, name, created_at),
        )
        row = db.execute(
            "SELECT id FROM projects WHERE user_id = %s AND name = %s",
            (user_id, name),
        ).fetchone()
        db.commit()
        return row["id"] if row else None

    def backfill_tasks_project(self, project_id):
        db = self._get_db()
        if self.user_id is None:
            return
        user_id = self.user_id
        db.execute(
            "UPDATE tasks SET project_id = %s WHERE user_id = %s AND (project_id IS NULL OR project_id = 0)",
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
                    %s::bigint AS now_ts,
                    %s::bigint AS rolling_start,
                    %s::bigint AS day_start
            )
            SELECT t.id, t.name, t.project_id, t.status, t.completed_at,
                   p.name AS project_name,
                   COALESCE(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           WHEN te.ended_at IS NULL THEN (
                               params.now_ts - EXTRACT(EPOCH FROM (CAST(te.started_at AS TIMESTAMP) AT TIME ZONE 'UTC'))
                           )
                           ELSE (
                               EXTRACT(EPOCH FROM (CAST(te.ended_at AS TIMESTAMP) AT TIME ZONE 'UTC'))
                               - EXTRACT(EPOCH FROM (CAST(te.started_at AS TIMESTAMP) AT TIME ZONE 'UTC'))
                           )
                       END
                   ), 0) AS total_seconds,
                   COALESCE(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           ELSE GREATEST(
                               0,
                               LEAST(
                                   COALESCE(EXTRACT(EPOCH FROM (CAST(te.ended_at AS TIMESTAMP) AT TIME ZONE 'UTC')), params.now_ts),
                                   params.now_ts
                               ) - GREATEST(
                                   EXTRACT(EPOCH FROM (CAST(te.started_at AS TIMESTAMP) AT TIME ZONE 'UTC')),
                                   params.rolling_start
                               )
                           )
                       END
                   ), 0) AS rolling_24h_seconds,
                   COALESCE(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           ELSE GREATEST(
                               0,
                               LEAST(
                                   COALESCE(EXTRACT(EPOCH FROM (CAST(te.ended_at AS TIMESTAMP) AT TIME ZONE 'UTC')), params.now_ts),
                                   params.now_ts
                               ) - GREATEST(
                                   EXTRACT(EPOCH FROM (CAST(te.started_at AS TIMESTAMP) AT TIME ZONE 'UTC')),
                                   params.day_start
                               )
                           )
                       END
                   ), 0) AS today_seconds,
                   MAX(CASE WHEN te.id IS NOT NULL AND te.ended_at IS NULL THEN 1 ELSE 0 END) AS is_running
            FROM tasks t
            CROSS JOIN params
            LEFT JOIN projects p ON p.id = t.project_id
            LEFT JOIN time_entries te ON te.task_id = t.id AND te.user_id = %s
            WHERE t.user_id = %s
            GROUP BY t.id, t.name, t.project_id, t.status, t.completed_at, p.name
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
                    %s::bigint AS now_ts,
                    %s::bigint AS rolling_start,
                    %s::bigint AS day_start
            )
            SELECT t.id, t.name, t.project_id, t.status, t.completed_at,
                   p.name AS project_name,
                   COALESCE(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           WHEN te.ended_at IS NULL THEN (
                               params.now_ts - EXTRACT(EPOCH FROM (CAST(te.started_at AS TIMESTAMP) AT TIME ZONE 'UTC'))
                           )
                           ELSE (
                               EXTRACT(EPOCH FROM (CAST(te.ended_at AS TIMESTAMP) AT TIME ZONE 'UTC'))
                               - EXTRACT(EPOCH FROM (CAST(te.started_at AS TIMESTAMP) AT TIME ZONE 'UTC'))
                           )
                       END
                   ), 0) AS total_seconds,
                   COALESCE(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           ELSE GREATEST(
                               0,
                               LEAST(
                                   COALESCE(EXTRACT(EPOCH FROM (CAST(te.ended_at AS TIMESTAMP) AT TIME ZONE 'UTC')), params.now_ts),
                                   params.now_ts
                               ) - GREATEST(
                                   EXTRACT(EPOCH FROM (CAST(te.started_at AS TIMESTAMP) AT TIME ZONE 'UTC')),
                                   params.rolling_start
                               )
                           )
                       END
                   ), 0) AS rolling_24h_seconds,
                   COALESCE(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           ELSE GREATEST(
                               0,
                               LEAST(
                                   COALESCE(EXTRACT(EPOCH FROM (CAST(te.ended_at AS TIMESTAMP) AT TIME ZONE 'UTC')), params.now_ts),
                                   params.now_ts
                               ) - GREATEST(
                                   EXTRACT(EPOCH FROM (CAST(te.started_at AS TIMESTAMP) AT TIME ZONE 'UTC')),
                                   params.day_start
                               )
                           )
                       END
                   ), 0) AS today_seconds,
                   MAX(CASE WHEN te.id IS NOT NULL AND te.ended_at IS NULL THEN 1 ELSE 0 END) AS is_running
            FROM tasks t
            CROSS JOIN params
            LEFT JOIN projects p ON p.id = t.project_id
            LEFT JOIN time_entries te ON te.task_id = t.id AND te.user_id = %s
            WHERE t.user_id = %s AND t.project_id = %s
            GROUP BY t.id, t.name, t.project_id, t.status, t.completed_at, p.name
            ORDER BY t.created_at DESC
            """,
            (now_ts, rolling_start, day_start, user_id, user_id, project_id),
        ).fetchall()
        return tasks

    def fetch_project(self, project_id):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            "SELECT id, name, created_at FROM projects WHERE id = %s AND user_id = %s",
            (project_id, user_id),
        ).fetchone()

    def create_task(self, name, created_at, project_id):
        db = self._get_db()
        user_id = self._require_user_id()
        cursor = db.execute(
            """
            INSERT INTO tasks (user_id, name, created_at, project_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, name, created_at, project_id),
        )
        row = cursor.fetchone()
        db.commit()
        return row["id"] if row else None

    def update_task(self, task_id, name):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "UPDATE tasks SET name = %s WHERE id = %s AND user_id = %s",
            (name, task_id, user_id),
        )
        db.commit()

    def set_task_status(self, task_id, status, completed_at):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "UPDATE tasks SET status = %s, completed_at = %s WHERE id = %s AND user_id = %s",
            (status, completed_at, task_id, user_id),
        )
        db.commit()

    def fetch_projects(self):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            "SELECT id, name, created_at FROM projects WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()

    def fetch_projects_by_ids(self, project_ids):
        if not project_ids:
            return []
        db = self._get_db()
        user_id = self._require_user_id()
        placeholders = ",".join(["%s"] * len(project_ids))
        return db.execute(
            f"""
            SELECT id, name, created_at
            FROM projects
            WHERE user_id = %s AND id IN ({placeholders})
            """,
            (user_id, *project_ids),
        ).fetchall()

    def create_project(self, name, created_at):
        db = self._get_db()
        user_id = self._require_user_id()
        cursor = db.execute(
            "INSERT INTO projects (user_id, name, created_at) VALUES (%s, %s, %s) RETURNING id",
            (user_id, name, created_at),
        )
        row = cursor.fetchone()
        db.commit()
        return row["id"] if row else None

    def update_project(self, project_id, name):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "UPDATE projects SET name = %s WHERE id = %s AND user_id = %s",
            (name, project_id, user_id),
        )
        db.commit()

    def delete_project(self, project_id):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            DELETE FROM time_entries
            WHERE user_id = %s AND task_id IN (
                SELECT id FROM tasks WHERE project_id = %s AND user_id = %s
            )
            """,
            (user_id, project_id, user_id),
        )
        db.execute(
            """
            DELETE FROM task_labels
            WHERE task_id IN (
                SELECT id FROM tasks WHERE project_id = %s AND user_id = %s
            )
            """,
            (project_id, user_id),
        )
        db.execute(
            "DELETE FROM project_labels WHERE project_id = %s",
            (project_id,),
        )
        db.execute("DELETE FROM tasks WHERE project_id = %s AND user_id = %s", (project_id, user_id))
        db.execute("DELETE FROM projects WHERE id = %s AND user_id = %s", (project_id, user_id))
        db.commit()

    def fetch_labels(self):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT id, name, color, created_at
            FROM labels
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()

    def fetch_tasks_by_project_ids(self, project_ids):
        if not project_ids:
            return []
        db = self._get_db()
        user_id = self._require_user_id()
        placeholders = ",".join(["%s"] * len(project_ids))
        return db.execute(
            f"""
            SELECT id, name, created_at, project_id
            FROM tasks
            WHERE user_id = %s AND project_id IN ({placeholders})
            """,
            (user_id, *project_ids),
        ).fetchall()

    def fetch_task_total_seconds(self, task_ids):
        if not task_ids:
            return {}
        db = self._get_db()
        user_id = self._require_user_id()
        placeholders = ",".join(["%s"] * len(task_ids))
        rows = db.execute(
            f"""
            SELECT t.id AS task_id,
                   COALESCE(SUM(
                       CASE
                           WHEN te.id IS NULL THEN 0
                           WHEN te.ended_at IS NULL THEN (
                               EXTRACT(EPOCH FROM NOW()) - EXTRACT(EPOCH FROM (CAST(te.started_at AS TIMESTAMP) AT TIME ZONE 'UTC'))
                           )
                           ELSE (
                               EXTRACT(EPOCH FROM (CAST(te.ended_at AS TIMESTAMP) AT TIME ZONE 'UTC'))
                               - EXTRACT(EPOCH FROM (CAST(te.started_at AS TIMESTAMP) AT TIME ZONE 'UTC'))
                           )
                       END
                   ), 0) AS total_seconds
            FROM tasks t
            LEFT JOIN time_entries te ON te.task_id = t.id AND te.user_id = %s
            WHERE t.user_id = %s AND t.id IN ({placeholders})
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
            "SELECT value FROM app_settings WHERE key = %s",
            (scoped_key,),
        ).fetchone()
        if row:
            return row["value"]
        if user_id is None:
            return None
        fallback = db.execute(
            "SELECT value FROM app_settings WHERE key = %s",
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
            VALUES (%s, %s)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (scoped_key, value),
        )
        db.commit()

    def create_label(self, name, color, created_at):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "INSERT INTO labels (user_id, name, color, created_at) VALUES (%s, %s, %s, %s)",
            (user_id, name, color, created_at),
        )
        db.commit()

    def update_label(self, label_id, name, color):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "UPDATE labels SET name = %s, color = %s WHERE id = %s AND user_id = %s",
            (name, color, label_id, user_id),
        )
        db.commit()

    def delete_label(self, label_id):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute("DELETE FROM task_labels WHERE label_id = %s", (label_id,))
        db.execute("DELETE FROM project_labels WHERE label_id = %s", (label_id,))
        db.execute("DELETE FROM labels WHERE id = %s AND user_id = %s", (label_id, user_id))
        db.commit()

    def add_label_to_task(self, task_id, label_id):
        db = self._get_db()
        db.execute(
            "INSERT INTO task_labels (task_id, label_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (task_id, label_id),
        )
        db.commit()

    def add_label_to_project(self, project_id, label_id):
        db = self._get_db()
        db.execute(
            "INSERT INTO project_labels (project_id, label_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (project_id, label_id),
        )
        db.commit()

    def set_project_labels(self, project_id, label_ids):
        db = self._get_db()
        user_id = self._require_user_id()
        owns_project = db.execute(
            "SELECT 1 FROM projects WHERE id = %s AND user_id = %s",
            (project_id, user_id),
        ).fetchone()
        if not owns_project:
            return
        cleaned_ids = []
        for label_id in label_ids or []:
            try:
                cleaned_ids.append(int(label_id))
            except (TypeError, ValueError):
                continue
        allowed_ids = set()
        if cleaned_ids:
            placeholders = ",".join(["%s"] * len(cleaned_ids))
            rows = db.execute(
                f"""
                SELECT id
                FROM labels
                WHERE user_id = %s AND id IN ({placeholders})
                """,
                (user_id, *cleaned_ids),
            ).fetchall()
            allowed_ids = {row["id"] for row in rows}
        db.execute("DELETE FROM project_labels WHERE project_id = %s", (project_id,))
        for label_id in sorted(allowed_ids):
            db.execute(
                "INSERT INTO project_labels (project_id, label_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
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
            WHERE user_id = %s
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
            WHERE id = %s AND user_id = %s
            """,
            (goal_id, user_id),
        ).fetchone()

    def create_goal(self, name, description, status, priority, target_date, target_seconds, created_at):
        db = self._get_db()
        user_id = self._require_user_id()
        cursor = db.execute(
            """
            INSERT INTO goals (user_id, name, description, status, priority, target_date, target_seconds, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, name, description, status, priority, target_date, target_seconds, created_at),
        )
        row = cursor.fetchone()
        db.commit()
        return row["id"] if row else None

    def update_goal(self, goal_id, name, description, status, priority, target_date, target_seconds):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            UPDATE goals
            SET name = %s, description = %s, status = %s, priority = %s, target_date = %s, target_seconds = %s
            WHERE id = %s AND user_id = %s
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
            WHERE goal_id IN (SELECT id FROM goals WHERE id = %s AND user_id = %s)
            """,
            (goal_id, user_id),
        )
        db.execute(
            """
            DELETE FROM goal_projects
            WHERE goal_id IN (SELECT id FROM goals WHERE id = %s AND user_id = %s)
            """,
            (goal_id, user_id),
        )
        db.execute(
            """
            DELETE FROM goal_subgoals
            WHERE goal_id IN (SELECT id FROM goals WHERE id = %s AND user_id = %s)
            """,
            (goal_id, user_id),
        )
        db.execute("DELETE FROM goals WHERE id = %s AND user_id = %s", (goal_id, user_id))
        db.commit()

    def fetch_goal_projects(self, goal_ids):
        if not goal_ids:
            return {}
        db = self._get_db()
        user_id = self._require_user_id()
        placeholders = ",".join(["%s"] * len(goal_ids))
        rows = db.execute(
            f"""
            SELECT gp.goal_id, gp.project_id
            FROM goal_projects gp
            JOIN goals g ON g.id = gp.goal_id
            WHERE g.user_id = %s AND gp.goal_id IN ({placeholders})
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
        placeholders = ",".join(["%s"] * len(goal_ids))
        rows = db.execute(
            f"""
            SELECT gt.goal_id, gt.task_id
            FROM goal_tasks gt
            JOIN goals g ON g.id = gt.goal_id
            WHERE g.user_id = %s AND gt.goal_id IN ({placeholders})
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
        placeholders = ",".join(["%s"] * len(goal_ids))
        rows = db.execute(
            f"""
            SELECT gs.id, gs.goal_id, gs.title, gs.label, gs.target_date, gs.project_id,
                   gs.status, gs.created_at
            FROM goal_subgoals gs
            JOIN goals g ON g.id = gs.goal_id
            WHERE g.user_id = %s AND gs.goal_id IN ({placeholders})
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
                    "label": row["label"],
                    "target_date": row["target_date"],
                    "project_id": row["project_id"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                }
            )
        return mapping

    def set_goal_projects(self, goal_id, project_ids):
        db = self._get_db()
        user_id = self._require_user_id()
        owns_goal = db.execute(
            "SELECT 1 FROM goals WHERE id = %s AND user_id = %s",
            (goal_id, user_id),
        ).fetchone()
        if not owns_goal:
            return
        db.execute("DELETE FROM goal_projects WHERE goal_id = %s", (goal_id,))
        for project_id in project_ids:
            db.execute(
                "INSERT INTO goal_projects (goal_id, project_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (goal_id, project_id),
            )
        db.commit()

    def set_goal_tasks(self, goal_id, task_ids):
        db = self._get_db()
        user_id = self._require_user_id()
        owns_goal = db.execute(
            "SELECT 1 FROM goals WHERE id = %s AND user_id = %s",
            (goal_id, user_id),
        ).fetchone()
        if not owns_goal:
            return
        db.execute("DELETE FROM goal_tasks WHERE goal_id = %s", (goal_id,))
        for task_id in task_ids:
            db.execute(
                "INSERT INTO goal_tasks (goal_id, task_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (goal_id, task_id),
            )
        db.commit()

    def set_goal_subgoals(self, goal_id, subgoal_titles, created_at):
        db = self._get_db()
        user_id = self._require_user_id()
        owns_goal = db.execute(
            "SELECT 1 FROM goals WHERE id = %s AND user_id = %s",
            (goal_id, user_id),
        ).fetchone()
        if not owns_goal:
            return
        db.execute("DELETE FROM goal_subgoals WHERE goal_id = %s", (goal_id,))
        for title in subgoal_titles:
            db.execute(
                """
                INSERT INTO goal_subgoals (goal_id, title, label, target_date, project_id, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (goal_id, title, None, None, None, "pending", created_at),
            )
        db.commit()

    def fetch_goal_subgoal(self, subgoal_id):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT gs.id, gs.goal_id, gs.title, gs.label, gs.target_date, gs.project_id,
                   gs.status, gs.created_at
            FROM goal_subgoals gs
            JOIN goals g ON g.id = gs.goal_id
            WHERE gs.id = %s AND g.user_id = %s
            """,
            (subgoal_id, user_id),
        ).fetchone()

    def set_goal_subgoal_status(self, subgoal_id, status):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            UPDATE goal_subgoals
            SET status = %s
            WHERE id = %s
              AND goal_id IN (SELECT id FROM goals WHERE user_id = %s)
            """,
            (status, subgoal_id, user_id),
        )
        db.commit()

    def add_goal_subgoal(self, goal_id, title, label, target_date, project_id, created_at):
        db = self._get_db()
        user_id = self._require_user_id()
        owns_goal = db.execute(
            "SELECT 1 FROM goals WHERE id = %s AND user_id = %s",
            (goal_id, user_id),
        ).fetchone()
        if not owns_goal:
            return
        db.execute(
            """
            INSERT INTO goal_subgoals (goal_id, title, label, target_date, project_id, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (goal_id, title, label, target_date, project_id, "pending", created_at),
        )
        db.commit()

    def fetch_habits(self):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT id, name, frequency, time_of_day, reminder, notes, goal_name, subgoal_name, created_at
            FROM habits
            WHERE user_id = %s
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
        cursor = db.execute(
            """
            INSERT INTO habits (
                user_id, name, frequency, time_of_day, reminder, notes, goal_name, subgoal_name, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
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
        row = cursor.fetchone()
        db.commit()
        return row["id"] if row else None

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
            SET name = %s, frequency = %s, time_of_day = %s, reminder = %s, notes = %s, goal_name = %s, subgoal_name = %s
            WHERE id = %s AND user_id = %s
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
            "DELETE FROM habit_logs WHERE habit_id IN (SELECT id FROM habits WHERE id = %s AND user_id = %s)",
            (habit_id, user_id),
        )
        db.execute("DELETE FROM habits WHERE id = %s AND user_id = %s", (habit_id, user_id))
        db.commit()

    def fetch_habit_logs_for_date(self, habit_ids, log_date):
        if not habit_ids:
            return set()
        db = self._get_db()
        placeholders = ",".join(["%s"] * len(habit_ids))
        rows = db.execute(
            f"""
            SELECT habit_id
            FROM habit_logs
            WHERE habit_id IN ({placeholders}) AND log_date = %s
            """,
            tuple(habit_ids) + (log_date,),
        ).fetchall()
        return {row["habit_id"] for row in rows}

    def fetch_habit_logs_map(self, habit_ids):
        if not habit_ids:
            return {}
        db = self._get_db()
        placeholders = ",".join(["%s"] * len(habit_ids))
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

    def fetch_reminders(self):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT id, title, notes, remind_date, remind_time, repeat_interval, repeat_days,
                   priority, channel_toast, channel_system, play_sound, is_active, created_at
            FROM reminders
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()

    def create_reminder(
        self,
        title,
        notes,
        remind_date,
        remind_time,
        repeat_interval,
        repeat_days,
        priority,
        channel_toast,
        channel_system,
        play_sound,
        is_active,
        created_at,
    ):
        db = self._get_db()
        user_id = self._require_user_id()
        cursor = db.execute(
            """
            INSERT INTO reminders (
                user_id, title, notes, remind_date, remind_time, repeat_interval, repeat_days,
                priority, channel_toast, channel_system, play_sound, is_active, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                title,
                notes,
                remind_date,
                remind_time,
                repeat_interval,
                repeat_days,
                priority,
                channel_toast,
                channel_system,
                play_sound,
                is_active,
                created_at,
            ),
        )
        row = cursor.fetchone()
        db.commit()
        return row["id"] if row else None

    def update_reminder(
        self,
        reminder_id,
        title,
        notes,
        remind_date,
        remind_time,
        repeat_interval,
        repeat_days,
        priority,
        channel_toast,
        channel_system,
        play_sound,
        is_active,
    ):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            UPDATE reminders
            SET title = %s, notes = %s, remind_date = %s, remind_time = %s, repeat_interval = %s,
                repeat_days = %s, priority = %s, channel_toast = %s, channel_system = %s,
                play_sound = %s, is_active = %s
            WHERE id = %s AND user_id = %s
            """,
            (
                title,
                notes,
                remind_date,
                remind_time,
                repeat_interval,
                repeat_days,
                priority,
                channel_toast,
                channel_system,
                play_sound,
                is_active,
                reminder_id,
                user_id,
            ),
        )
        db.commit()

    def set_reminder_active(self, reminder_id, is_active):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "UPDATE reminders SET is_active = %s WHERE id = %s AND user_id = %s",
            (1 if is_active else 0, reminder_id, user_id),
        )
        db.commit()

    def delete_reminder(self, reminder_id):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "DELETE FROM reminders WHERE id = %s AND user_id = %s",
            (reminder_id, user_id),
        )
        db.commit()

    def fetch_todos_for_date(self, log_date):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT id, name, log_date, created_at, completed_at
            FROM daily_todos
            WHERE user_id = %s AND log_date = %s
            ORDER BY created_at DESC
            """,
            (user_id, log_date),
        ).fetchall()

    def create_todo(self, name, log_date, created_at):
        db = self._get_db()
        user_id = self._require_user_id()
        cursor = db.execute(
            """
            INSERT INTO daily_todos (user_id, name, log_date, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, name, log_date, created_at),
        )
        row = cursor.fetchone()
        db.commit()
        return row["id"] if row else None

    def set_todo_completed(self, todo_id, completed_at):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "UPDATE daily_todos SET completed_at = %s WHERE id = %s AND user_id = %s",
            (completed_at, todo_id, user_id),
        )
        db.commit()

    def delete_todo(self, todo_id):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "DELETE FROM daily_todos WHERE id = %s AND user_id = %s",
            (todo_id, user_id),
        )
        db.commit()

    def set_habit_log(self, habit_id, log_date, done):
        db = self._get_db()
        if done:
            db.execute(
                """
                INSERT INTO habit_logs (habit_id, log_date, created_at)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (habit_id, log_date, datetime.utcnow().isoformat()),
            )
        else:
            db.execute(
                "DELETE FROM habit_logs WHERE habit_id = %s AND log_date = %s",
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
            WHERE habit_id IN (SELECT id FROM habits WHERE user_id = %s)
              AND log_date BETWEEN %s AND %s
            GROUP BY log_date
            ORDER BY log_date ASC
            """,
            (user_id, start_date, end_date),
        ).fetchall()
        return {row["log_date"]: row["total"] for row in rows}

    def fetch_goals_created_count(self, start_iso, end_iso):
        db = self._get_db()
        user_id = self._require_user_id()
        row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM goals
            WHERE user_id = %s AND created_at BETWEEN %s AND %s
            """,
            (user_id, start_iso, end_iso),
        ).fetchone()
        return int(row["total"] or 0)

    def fetch_goal_status_counts(self, start_iso, end_iso):
        db = self._get_db()
        user_id = self._require_user_id()
        rows = db.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM goals
            WHERE user_id = %s AND created_at BETWEEN %s AND %s
            GROUP BY status
            """,
            (user_id, start_iso, end_iso),
        ).fetchall()
        return {row["status"]: int(row["total"] or 0) for row in rows}

    def fetch_goal_due_count(self, start_date, end_date):
        db = self._get_db()
        user_id = self._require_user_id()
        row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM goals
            WHERE user_id = %s
              AND target_date IS NOT NULL
              AND target_date BETWEEN %s AND %s
            """,
            (user_id, start_date, end_date),
        ).fetchone()
        return int(row["total"] or 0)

    def fetch_habits_created_count(self, start_iso, end_iso):
        db = self._get_db()
        user_id = self._require_user_id()
        row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM habits
            WHERE user_id = %s AND created_at BETWEEN %s AND %s
            """,
            (user_id, start_iso, end_iso),
        ).fetchone()
        return int(row["total"] or 0)

    def fetch_total_habits_count(self):
        db = self._get_db()
        user_id = self._require_user_id()
        row = db.execute(
            "SELECT COUNT(*) AS total FROM habits WHERE user_id = %s",
            (user_id,),
        ).fetchone()
        return int(row["total"] or 0)

    def fetch_habit_log_stats(self, start_date, end_date):
        db = self._get_db()
        user_id = self._require_user_id()
        row = db.execute(
            """
            SELECT COUNT(*) AS total_logs,
                   COUNT(DISTINCT habit_id) AS active_habits,
                   COUNT(DISTINCT log_date) AS active_days
            FROM habit_logs
            WHERE habit_id IN (SELECT id FROM habits WHERE user_id = %s)
              AND log_date BETWEEN %s AND %s
            """,
            (user_id, start_date, end_date),
        ).fetchone()
        return {
            "total_logs": int(row["total_logs"] or 0),
            "active_habits": int(row["active_habits"] or 0),
            "active_days": int(row["active_days"] or 0),
        }

    def fetch_projects_created_count(self, start_iso, end_iso):
        db = self._get_db()
        user_id = self._require_user_id()
        row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM projects
            WHERE user_id = %s AND created_at BETWEEN %s AND %s
            """,
            (user_id, start_iso, end_iso),
        ).fetchone()
        return int(row["total"] or 0)

    def fetch_tasks_created_count(self, start_iso, end_iso):
        db = self._get_db()
        user_id = self._require_user_id()
        row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM tasks
            WHERE user_id = %s AND created_at BETWEEN %s AND %s
            """,
            (user_id, start_iso, end_iso),
        ).fetchone()
        return int(row["total"] or 0)

    def fetch_tasks_completed_count(self, start_iso, end_iso):
        db = self._get_db()
        user_id = self._require_user_id()
        row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM tasks
            WHERE user_id = %s
              AND completed_at IS NOT NULL
              AND completed_at BETWEEN %s AND %s
            """,
            (user_id, start_iso, end_iso),
        ).fetchone()
        return int(row["total"] or 0)

    def fetch_task_labels_map(self, task_ids):
        if not task_ids:
            return {}
        db = self._get_db()
        user_id = self._require_user_id()
        placeholders = ",".join(["%s"] * len(task_ids))
        rows = db.execute(
            f"""
            SELECT tl.task_id, l.id, l.name, l.color
            FROM task_labels tl
            JOIN labels l ON l.id = tl.label_id
            JOIN tasks t ON t.id = tl.task_id
            WHERE t.user_id = %s AND l.user_id = %s AND tl.task_id IN ({placeholders})
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
        placeholders = ",".join(["%s"] * len(task_ids))
        rows = db.execute(
            f"""
            SELECT task_id
            FROM task_daily_checks
            WHERE task_id IN ({placeholders}) AND log_date = %s
            """,
            tuple(task_ids) + (log_date,),
        ).fetchall()
        return {row["task_id"] for row in rows}

    def fetch_task_daily_check_counts(self, task_ids):
        if not task_ids:
            return {}
        db = self._get_db()
        placeholders = ",".join(["%s"] * len(task_ids))
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
                INSERT INTO task_daily_checks (task_id, log_date, created_at)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (task_id, log_date, datetime.utcnow().isoformat()),
            )
        else:
            db.execute(
                "DELETE FROM task_daily_checks WHERE task_id = %s AND log_date = %s",
                (task_id, log_date),
            )
        db.commit()

    def fetch_project_labels_map(self, project_ids):
        if not project_ids:
            return {}
        db = self._get_db()
        user_id = self._require_user_id()
        placeholders = ",".join(["%s"] * len(project_ids))
        rows = db.execute(
            f"""
            SELECT pl.project_id, l.id, l.name, l.color
            FROM project_labels pl
            JOIN labels l ON l.id = pl.label_id
            JOIN projects p ON p.id = pl.project_id
            WHERE p.user_id = %s AND l.user_id = %s AND pl.project_id IN ({placeholders})
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
            WHERE task_id = %s AND ended_at IS NULL AND user_id = %s
            """,
            (task_id, user_id),
        ).fetchone()
        return row is not None

    def start_task(self, task_id, started_at):
        db = self._get_db()
        user_id = self._require_user_id()
        owns_task = db.execute(
            "SELECT 1 FROM tasks WHERE id = %s AND user_id = %s",
            (task_id, user_id),
        ).fetchone()
        if not owns_task:
            return
        db.execute(
            "INSERT INTO time_entries (user_id, task_id, started_at) VALUES (%s, %s, %s)",
            (user_id, task_id, started_at),
        )
        db.commit()

    def stop_task(self, task_id, ended_at):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            UPDATE time_entries
            SET ended_at = %s
            WHERE task_id = %s AND ended_at IS NULL AND user_id = %s
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
            WHERE ended_at IS NULL AND user_id = %s
            """,
            (user_id,),
        ).fetchall()

    def stop_time_entry(self, entry_id, ended_at):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            """
            UPDATE time_entries
            SET ended_at = %s
            WHERE id = %s AND user_id = %s
            """,
            (ended_at, entry_id, user_id),
        )
        db.commit()

    def delete_task(self, task_id):
        db = self._get_db()
        user_id = self._require_user_id()
        db.execute(
            "DELETE FROM time_entries WHERE task_id = %s AND user_id = %s",
            (task_id, user_id),
        )
        db.execute("DELETE FROM task_labels WHERE task_id = %s", (task_id,))
        db.execute("DELETE FROM task_daily_checks WHERE task_id = %s", (task_id,))
        db.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", (task_id, user_id))
        db.commit()

    def fetch_time_entries_between(self, start_iso, end_iso):
        db = self._get_db()
        user_id = self._require_user_id()
        return db.execute(
            """
            SELECT id, task_id, started_at, ended_at
            FROM time_entries
            WHERE user_id = %s
              AND started_at < %s
              AND (ended_at IS NULL OR ended_at > %s)
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
            WHERE te.user_id = %s
              AND t.user_id = %s
              AND te.started_at < %s
              AND (te.ended_at IS NULL OR te.ended_at > %s)
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
            WHERE te.user_id = %s
              AND t.user_id = %s
              AND te.started_at < %s
              AND (te.ended_at IS NULL OR te.ended_at > %s)
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
            WHERE te.user_id = %s
              AND l.user_id = %s
              AND te.started_at < %s
              AND (te.ended_at IS NULL OR te.ended_at > %s)
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
            WHERE te.user_id = %s
              AND t.user_id = %s
              AND te.started_at < %s
              AND (te.ended_at IS NULL OR te.ended_at > %s)
            ORDER BY te.started_at DESC
            """,
            (user_id, user_id, end_iso, start_iso),
        ).fetchall()
