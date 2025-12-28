import os
import random
import sqlite3
from datetime import datetime, timedelta


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "data.db")


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def seed_db():
    ensure_dir(os.path.dirname(DB_PATH))
    random.seed(42)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")

    # Clear existing data to keep seed deterministic.
    cur.executescript(
        """
        DELETE FROM time_entries;
        DELETE FROM task_labels;
        DELETE FROM project_labels;
        DELETE FROM tasks;
        DELETE FROM projects;
        """
    )
    conn.commit()

    now = datetime.utcnow()
    start_day = (now - timedelta(days=90)).replace(hour=0, minute=0, second=0, microsecond=0)

    project_ids = []
    for idx in range(1, 4):
        name = f"Project {idx}"
        created_at = (start_day - timedelta(days=idx)).isoformat()
        cur.execute(
            "INSERT INTO projects (name, created_at) VALUES (?, ?)",
            (name, created_at),
        )
        project_ids.append(cur.lastrowid)

    task_ids = []
    for project_id in project_ids:
        for t_idx in range(1, 6):
            task_name = f"Task {t_idx} (P{project_id})"
            created_at = (start_day + timedelta(days=t_idx)).isoformat()
            cur.execute(
                "INSERT INTO tasks (name, created_at, project_id) VALUES (?, ?, ?)",
                (task_name, created_at, project_id),
            )
            task_ids.append(cur.lastrowid)

    for day_offset in range(0, 90):
        day_start = start_day + timedelta(days=day_offset)
        for task_id in task_ids:
            # Random session around ~1 hour per day per task.
            duration_minutes = random.randint(35, 90)
            start_minute = random.randint(8 * 60, 20 * 60)
            started_at = day_start + timedelta(minutes=start_minute)
            ended_at = started_at + timedelta(minutes=duration_minutes)
            cur.execute(
                "INSERT INTO time_entries (task_id, started_at, ended_at) VALUES (?, ?, ?)",
                (task_id, started_at.isoformat(), ended_at.isoformat()),
            )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed_db()
    print(f"Seeded data into {DB_PATH}")
