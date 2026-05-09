# Goalixa Core-API

Production backend service for the Goalixa productivity platform. Handles all business logic for task tracking, time entries, goals, projects, habits, reminders, and comprehensive reporting.

## Overview

Core-API is the main backend service in the Goalixa microservices architecture. It provides a comprehensive REST API for managing productivity data and integrates with the authentication service for secure access control.

**Key Responsibilities**:
- Task management with timer functionality (start/stop tracking)
- Project and goal tracking with hierarchical relationships
- Habit tracking with daily logging
- Time entry management and reporting
- Daily todos and weekly goals
- Label system for organization
- Reminder notifications

## Architecture

### 3-Layer Design Pattern

```
┌─────────────────────────────────────┐
│     Presentation Layer (Routes)     │  ← HTTP endpoints
│      app/presentation/*.py          │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│      Service Layer (Logic)          │  ← Business rules
│       app/service/*.py               │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│   Repository Layer (Data Access)    │  ← PostgreSQL queries
│      app/repository/*.py             │
└─────────────────────────────────────┘
```

**Dependency Injection**: Wired in `main.py` for clean separation and testability.

## Features

### Core Functionality
- **Tasks**: CRUD operations, status management, timer tracking (start/stop/pause)
- **Projects**: Task organization and project-level reporting
- **Goals**: Goal tracking with project/task relationships
- **Habits**: Daily habit logging with streak tracking
- **Time Entries**: Automatic time tracking from task timers
- **Reminders**: Date-based reminder system
- **Labels**: Color-coded labels for organizing tasks
- **Reports**: Comprehensive analytics and productivity insights

### Technical Features
- **Health Checks**: `/health` endpoint for Kubernetes probes
- **Metrics**: Prometheus metrics at `/metrics` for observability
- **Request Logging**: Structured logging with configurable levels
- **Error Handling**: Consistent error responses across all endpoints
- **Database Migrations**: Schema evolution support

## Tech Stack

- **Python 3.11** - Modern Python features
- **Flask** - Lightweight WSGI framework
- **PostgreSQL** - Relational database with JSONB support
- **SQLAlchemy** - ORM and database toolkit
- **Prometheus** - Metrics collection
- **Docker** - Containerization
- **Kubernetes** - Orchestration (production)

## Project Structure

```
Core-API/
├── app/
│   ├── presentation/          # API routes and controllers
│   │   ├── tasks_controller.py
│   │   ├── projects_controller.py
│   │   ├── goals_controller.py
│   │   └── ...
│   ├── service/               # Business logic
│   │   ├── task_service.py
│   │   ├── project_service.py
│   │   └── ...
│   └── repository/            # Data access layer
│       ├── task_repository.py
│       ├── project_repository.py
│       └── ...
├── helm/                      # Helm chart for K8s deployment
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
├── .argo/                     # ArgoCD deployment config
│   └── app.yaml
├── main.py                    # Application entry point + DI wiring
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container image definition
└── docker-compose.yml         # Local development setup
```

## Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Docker (optional, for containerized setup)

### Setup with Virtual Environment

1. **Create virtual environment**:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure database**:
```bash
export DATABASE_URL="postgresql://goalixa:goalixa@localhost:5432/goalixa"
export AUTH_JWT_SECRET="your-jwt-secret-here"
```

4. **Run the application**:
```bash
python3 main.py
```

5. **Verify installation**:
```bash
curl http://localhost:5000/health
# Should return: {"status": "healthy"}
```

### Setup with Docker Compose

```bash
docker-compose up --build
```

This starts both the API server and PostgreSQL database.

Access the API at `http://localhost:5000`.

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | ✅ |
| `AUTH_JWT_SECRET` | JWT secret for token validation | - | ✅ |
| `AUTH_ACCESS_TOKEN_TTL_MINUTES` | Access token TTL | `15` | ❌ |
| `AUTH_REFRESH_TOKEN_TTL_DAYS` | Refresh token TTL | `7` | ❌ |
| `LOG_LEVEL` | Logging level | `INFO` | ❌ |
| `LOG_FORMAT` | Log message format | standard | ❌ |
| `LOG_DATE_FORMAT` | Timestamp format | ISO 8601 | ❌ |
| `LOG_REQUESTS_ENABLED` | Enable request logging | `1` | ❌ |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | - | ❌ |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret | - | ❌ |

### Database Schema

14 tables organized by domain:

- **User Management**: `user`, `refresh_token`
- **Task Management**: `tasks`, `task_labels`, `task_daily_checks`, `time_entries`
- **Organization**: `projects`, `labels`
- **Goals & Habits**: `goals`, `goal_projects`, `goal_tasks`, `goal_subgoals`, `habits`, `habit_logs`
- **Planning**: `daily_todos`, `weekly_goals`, `reminders`

See database migrations for full schema details.

## API Endpoints

### Health & Monitoring
- `GET /health` - Health check (Kubernetes probes)
- `GET /metrics` - Prometheus metrics

### Tasks
- `GET /api/tasks` - List all tasks
- `POST /api/tasks` - Create new task
- `GET /api/tasks/{id}` - Get task details
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task
- `POST /api/tasks/{id}/start` - Start task timer
- `POST /api/tasks/{id}/stop` - Stop task timer

### Projects
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create project
- `GET /api/projects/{id}` - Get project details
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project

### Goals, Habits, Time Entries, etc.
Similar CRUD patterns for:
- `/api/goals/*` - Goal management
- `/api/habits/*` - Habit tracking
- `/api/time-entries/*` - Time logging
- `/api/reminders/*` - Reminder management
- `/api/labels/*` - Label management
- `/api/reports/*` - Analytics and reporting

For complete API documentation, see the Swagger/OpenAPI spec (if available) or explore via the BFF service.

## Deployment

### Docker Build
```bash
docker build -t harbor.goalixa.com/goalixa/core-api:latest .
docker push harbor.goalixa.com/goalixa/core-api:latest
```

### Kubernetes with Helm
```bash
# Install/upgrade via Helm
helm upgrade --install core-api ./helm \
  --namespace goalixa-core-api \
  --create-namespace \
  --values ./helm/values.yaml
```

### GitOps with ArgoCD
The `.argo/app.yaml` file defines the ArgoCD Application. ArgoCD automatically syncs from the Git repository.

```bash
# Apply ArgoCD application
kubectl apply -f .argo/app.yaml
```

### CI/CD Pipeline
GitHub Actions workflow (`.github/workflows/main.yml`):
1. Build Docker image on push to `main`
2. Push to Harbor registry
3. Update ArgoCD application with new image tag
4. ArgoCD syncs deployment automatically

## Observability

### Prometheus Metrics
- `flask_http_request_duration_seconds` - Request latency histogram
- `flask_http_request_total` - Request count by method/endpoint/status
- `process_*` - Process-level metrics (CPU, memory, etc.)

### Logging
Structured logs with request ID tracking:
```json
{
  "timestamp": "2026-05-04T10:30:00Z",
  "level": "INFO",
  "message": "Request completed",
  "method": "GET",
  "path": "/api/tasks",
  "status": 200,
  "duration_ms": 45.23
}
```

### Health Checks
```bash
# Basic health
curl http://localhost:5000/health

# Kubernetes liveness probe
GET /health

# Database connectivity check
# (implicitly verified via /health)
```

## Integration with Goalixa Platform

Core-API integrates with other Goalixa services:

- **goalixa-auth**: Token validation (JWT), user authentication
- **goalixa-BFF**: Frontend API gateway, request aggregation
- **goalixa-pwa**: Frontend client consuming the API

**Authentication Flow**:
1. User authenticates via `goalixa-auth`
2. Receives JWT access token (15min) + refresh token (7 days)
3. Frontend includes access token in requests to BFF
4. BFF proxies requests to Core-API with token
5. Core-API validates JWT signature using `AUTH_JWT_SECRET`

## Development Guidelines

### Adding New Features
1. **Create repository method** - Data access in `app/repository/`
2. **Implement service logic** - Business rules in `app/service/`
3. **Add controller endpoint** - HTTP routes in `app/presentation/`
4. **Wire dependencies** - Update DI in `main.py`
5. **Test locally** - Use docker-compose for integration testing

### Code Style
- Follow PEP 8 conventions
- Use type hints for function signatures
- Document complex business logic
- Keep layers separated (no repository calls from controllers)

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check environment variable
echo $DATABASE_URL
```

### JWT Token Errors
- Ensure `AUTH_JWT_SECRET` matches the auth service
- Check token expiration time
- Verify token format in request headers

### Port Already in Use
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9
```

## Performance

**Targets**:
- API response time: < 100ms (p95)
- Database query time: < 50ms (p95)
- Concurrent requests: 100+ RPS

**Optimization**:
- Database indexes on frequently queried columns
- Connection pooling (SQLAlchemy engine)
- Caching at BFF layer (Redis)

## License

Internal Goalixa Service - Proprietary

---

**Last Updated**: 2026-05-04
**Version**: 2.0.0
**Cluster**: Kubeadm (4 nodes)
**Production URL**: Accessed via `api.goalixa.com/app/*` (through BFF)
