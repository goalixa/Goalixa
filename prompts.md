# Goalixa App Repository

## Purpose
Main Flask application for task and time tracking with goals, plans, projects, and tasks management.

## Architecture
3-layer architecture with dependency injection:
- **Presentation Layer**: Routes and filters (`app/presentation/`)
- **Service Layer**: Business logic (`app/service/`)
- **Repository Layer**: Data access (`app/repository/`)

## Tech Stack
- **Python 3.11** + Flask
- **PostgreSQL** (via psycopg2-binary)
- **Flask-SQLAlchemy** for ORM
- **Authentication**: Integrates with goalixa-auth service via JWT cookies

## Key Configuration
Environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `AUTH_SERVICE_URL`: Auth service URL (default: https://goalixa.com/auth)
- `AUTH_JWT_SECRET`: Shared JWT secret with auth service
- `AUTH_ACCESS_COOKIE_NAME`: Access token cookie name (default: goalixa_access)
- `AUTH_REFRESH_COOKIE_NAME`: Refresh token cookie name (default: goalixa_refresh)
- `AUTH_ACCESS_TOKEN_TTL_MINUTES`: Access token TTL (default: 15)
- `AUTH_REFRESH_TOKEN_TTL_DAYS`: Refresh token TTL (default: 7)
- `AUTH_COOKIE_DOMAIN`: Cookie domain (default: .goalixa.com)
- `AUTH_COOKIE_SAMESITE`: SameSite policy (default: Lax)
- `AUTH_COOKIE_SECURE`: Secure cookies flag (default: 0)
- `SKIP_AUTH`: Disable authentication for development (default: 0)
- `DEMO_MODE_ENABLED`: Enable demo mode (default: 0)
- `DEMO_USER_ID`: Demo mode user ID
- `DEMO_SEED_KEY`: Key for seeding demo data

## Code Conventions
- Use `create_app()` factory pattern
- Load config via `os.getenv()` with sensible defaults
- Use ProxyFix for proper proxy header handling
- Inject repositories and services into routes
- Use `@login_required` decorator for protected routes
- Use structured logging: `app.logger.info("message", extra={"key": "value"})`
- CSS cache-busting via `CSS_VERSION` config (timestamp on restart)

## File Structure
```
Goalixa-app/
├── main.py                 # Application factory
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── app/
│   ├── __init__.py
│   ├── auth_client.py      # Auth service integration
│   ├── presentation/
│   │   ├── routes.py       # HTTP routes
│   │   └── filters.py      # Jinja filters
│   ├── service/
│   │   └── task_service.py # Business logic
│   └── repository/
│       └── postgres_repository.py  # Data access
```

## Authentication Flow
1. User receives JWT cookies from auth service
2. App validates cookies using shared JWT secret
3. User info extracted from access token
4. Refresh token used for auto-refresh if access expired
