# Goalixa Core-API

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791?logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

Backend service for the Goalixa productivity platform. Handles task tracking, time entries, goals, projects, habits, reminders, and reporting.

## Features

| Feature | Description |
|---------|-------------|
| **Tasks** | CRUD operations, status management, timer tracking |
| **Projects** | Task organization, project-level reporting |
| **Goals** | Goal tracking with project/task relationships |
| **Habits** | Daily habit logging with streak tracking |
| **Time Entries** | Automatic time tracking from task timers |
| **Reminders** | Date-based reminder system |
| **Labels** | Color-coded labels for organizing tasks |
| **Reports** | Analytics and productivity insights |

## Architecture

```
┌─────────────────────────────────────┐
│     Presentation Layer (Routes)     │
│        app/presentation/*.py        │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│       Service Layer (Logic)         │
│         app/service/*.py            │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│   Repository Layer (Data Access)    │
│        app/repository/*.py          │
└─────────────────────────────────────┘
```

## Tech Stack

- **Python 3.11**
- **Flask** - Web framework
- **PostgreSQL** - Database
- **SQLAlchemy** - ORM
- **Prometheus** - Metrics
- **Docker** - Containerization

## Project Structure

```
Core-API/
├── app/
│   ├── presentation/      # API routes
│   ├── service/           # Business logic
│   └── repository/        # Data access
├── helm/                  # Kubernetes deployment
├── main.py                # Entry point
├── requirements.txt
└── Dockerfile
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Docker (optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/goalixa/core-api.git
cd core-api

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/goalixa
JWT_SECRET=your-secret-key
```

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `JWT_SECRET` | Secret for JWT validation | Yes |
| `LOG_LEVEL` | Logging level | No |

### Run

```bash
# Development
python3 main.py

# With Docker
docker-compose up --build
```

The API runs at `http://localhost:5000`.

## API Endpoints

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks` | List tasks |
| POST | `/api/tasks` | Create task |
| GET | `/api/tasks/{id}` | Get task |
| PUT | `/api/tasks/{id}` | Update task |
| DELETE | `/api/tasks/{id}` | Delete task |
| POST | `/api/tasks/{id}/start` | Start timer |
| POST | `/api/tasks/{id}/stop` | Stop timer |

### Other Resources

- `/api/projects/*` - Project management
- `/api/goals/*` - Goal tracking
- `/api/habits/*` - Habit tracking
- `/api/time-entries/*` - Time logging
- `/api/reminders/*` - Reminders
- `/api/labels/*` - Labels
- `/api/reports/*` - Reports

## Database Schema

```
user
├── projects
├── labels
├── tasks
│   ├── task_labels
│   ├── time_entries
│   └── task_daily_checks
├── goals
│   ├── goal_projects
│   ├── goal_tasks
│   └── goal_subgoals
├── habits
│   └── habit_logs
├── reminders
├── daily_todos
└── weekly_goals
```

## Deployment

### Docker

```bash
docker build -t goalixa-core-api:latest .
docker run -p 5000:80 goalixa-core-api:latest
```

### Kubernetes

```bash
helm upgrade --install core-api ./helm \
  --namespace goalixa \
  --create-namespace
```

## Development

### Adding Features

1. Create repository method in `app/repository/`
2. Implement service logic in `app/service/`
3. Add controller endpoint in `app/presentation/`
4. Wire dependencies in `main.py`

### Code Style

- Follow PEP 8
- Use type hints
- Keep layers separated

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built by [Amirreza Rezaie](https://github.com/amirrezarezaie)
