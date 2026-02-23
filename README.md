# Goalixa

Backend-only Flask API for tracking tasks, time entries, goals, projects, habits, reminders, and reports. Uses PostgreSQL for storage and follows a 3-layer structure (presentation, service, repository).

## Features
- JSON APIs under `/api/*`
- Auth endpoints under `/api/auth/*`
- Task timer tracking, goals, habits, reminders, reports, and settings
- Prometheus metrics endpoint at `/metrics`

## Tech Stack
- Python 3.11
- Flask
- PostgreSQL
- Docker / Docker Compose

## Project Structure
- `app/presentation/` API routes
- `app/service/` business logic
- `app/repository/` data access (PostgreSQL)
- `main.py` app entrypoint and wiring (DI)

## Local Setup
1) Create a virtual environment and install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Start PostgreSQL and set `DATABASE_URL`:
```bash
export DATABASE_URL="postgresql://goalixa:goalixa@localhost:5432/goalixa"
```

3) Run the app:
```bash
python3 main.py
```

Check `http://localhost:5000/health` and call API routes at `http://localhost:5000/api/...`.
Prometheus metrics are available at `http://localhost:5000/metrics`.

## Logging Configuration
The application logs to stdout and supports these environment variables:

- `LOG_LEVEL` (default: `INFO`)
- `LOG_FORMAT` (default: `%(asctime)s %(levelname)s [%(name)s] %(message)s`)
- `LOG_DATE_FORMAT` (default: `%Y-%m-%dT%H:%M:%S%z`)
- `LOG_REQUESTS_ENABLED` (`1`/`0`, default: `1`)

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

Check `http://localhost:5000/health`.

## Database
PostgreSQL is used for storage. Configure the connection via `DATABASE_URL`.

## Notes
- This is a learning project focused on 3-layer architecture and basic DI.
