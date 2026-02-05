import os
import random
from datetime import datetime, timedelta

from flask import Flask
from dotenv import load_dotenv

from app.repository.postgres_repository import PostgresTaskRepository


def seed_db():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set (e.g. postgresql://user:pass@host:5432/db)")
    seed_user_id = int(os.getenv("SEED_USER_ID", "1"))
    seed_user_email = os.getenv("SEED_USER_EMAIL", "seed@goalixa.local")

    random.seed(42)
    app = Flask(__name__)
    repository = PostgresTaskRepository(database_url)

    with app.app_context():
        repository.init_db()
        repository.set_user_id(seed_user_id)
        repository.ensure_user(seed_user_email)
        db = repository._get_db()

        # Clear existing data for the seed user to keep the seed deterministic.
        db.execute("DELETE FROM time_entries WHERE user_id = %s", (seed_user_id,))
        db.execute(
            """
            DELETE FROM task_labels
            WHERE task_id IN (SELECT id FROM tasks WHERE user_id = %s)
            """,
            (seed_user_id,),
        )
        db.execute(
            """
            DELETE FROM project_labels
            WHERE project_id IN (SELECT id FROM projects WHERE user_id = %s)
            """,
            (seed_user_id,),
        )
        db.execute("DELETE FROM tasks WHERE user_id = %s", (seed_user_id,))
        db.execute("DELETE FROM projects WHERE user_id = %s", (seed_user_id,))
        db.commit()

        now = datetime.utcnow()
        start_day = (now - timedelta(days=90)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        project_names = ["Cloud Migration", "Mobile App Redesign", "Data Platform"]
        project_ids = []
        for idx, name in enumerate(project_names, start=1):
            created_at = (start_day - timedelta(days=idx)).isoformat()
            row = db.execute(
                "INSERT INTO projects (user_id, name, created_at) VALUES (%s, %s, %s) RETURNING id",
                (seed_user_id, name, created_at),
            ).fetchone()
            project_ids.append(row["id"])

        task_names_by_project = {
            "Cloud Migration": [
                "Inventory Legacy Services",
                "Design VPC Architecture",
                "Set Up CI/CD Pipeline",
                "Migrate Auth Service",
                "Load Test Cutover",
            ],
            "Mobile App Redesign": [
                "Wireframe Key Screens",
                "Build Design System",
                "Implement New Onboarding",
                "Refactor Navigation",
                "Accessibility QA",
            ],
            "Data Platform": [
                "Ingest Raw Events",
                "Normalize Schemas",
                "Build ETL Jobs",
                "Define Metrics Layer",
                "Create Daily Dashboards",
            ],
        }

        task_ids = []
        for project_id, project_name in zip(project_ids, project_names):
            for t_idx, task_name in enumerate(task_names_by_project[project_name], start=1):
                created_at = (start_day + timedelta(days=t_idx)).isoformat()
                row = db.execute(
                    """
                    INSERT INTO tasks (user_id, name, created_at, project_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (seed_user_id, task_name, created_at, project_id),
                ).fetchone()
                task_ids.append(row["id"])

        for day_offset in range(0, 90):
            day_start = start_day + timedelta(days=day_offset)
            for task_id in task_ids:
                # Random session around ~1 hour per day per task.
                duration_minutes = random.randint(35, 90)
                start_minute = random.randint(8 * 60, 20 * 60)
                started_at = day_start + timedelta(minutes=start_minute)
                ended_at = started_at + timedelta(minutes=duration_minutes)
                db.execute(
                    """
                    INSERT INTO time_entries (user_id, task_id, started_at, ended_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (seed_user_id, task_id, started_at.isoformat(), ended_at.isoformat()),
                )

        db.commit()


if __name__ == "__main__":
    seed_db()
    print("Seeded data into PostgreSQL.")
