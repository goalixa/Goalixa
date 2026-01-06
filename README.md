# Focus (StudyTimer)

Simple Flask app to track tasks and time spent per task. Uses SQLite for storage and follows a 3-layer structure (presentation, service, repository) to demonstrate basic dependency injection.

## Features
- Create tasks
- Start/stop timer per task
- See total time per task

## Tech Stack
- Python 3.11
- Flask
- SQLite
- Docker / Docker Compose

## Project Structure
- `app/presentation/` routes and template filters
- `app/service/` business logic
- `app/repository/` data access (SQLite)
- `templates/` HTML templates
- `static/` CSS
- `main.py` app entrypoint and wiring (DI)

## Local Setup
1) Create a virtual environment and install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Create the data directory (SQLite file will be created inside it):
```bash
mkdir -p data
```

3) Run the app:
```bash
python3 main.py
```

Open `http://localhost:5000`.

## Google OAuth (optional)
To enable "Continue with Google" sign-in, set these environment variables before starting the app:

```bash
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
```

Make sure your Google OAuth consent screen has the redirect URI:
`http://localhost:5000/login/google/callback`

## Docker
Build and run:
```bash
docker compose up --build
```

If you do not have a `data` directory yet:
```bash
mkdir -p data
```

Open `http://localhost:5000`.

## Database
SQLite file is stored at `data/data.db` and is ignored by Git.

## Notes
- This is a learning project focused on 3-layer architecture and basic DI.
- For multi-user or heavier workloads, consider PostgreSQL.
