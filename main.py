import os

from dotenv import load_dotenv

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.observability import configure_logging, register_observability
from app.auth_client import init_auth

from app.auth.routes import register_auth_routes
from app.presentation.routes import register_routes
from app.repository.postgres_repository import PostgresTaskRepository
from app.service.task_service import TaskService


def create_app():
    load_dotenv()
    configure_logging()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["AUTH_JWT_SECRET"] = os.getenv("AUTH_JWT_SECRET", "dev-jwt-secret")
    app.config["AUTH_COOKIE_NAME"] = os.getenv("AUTH_COOKIE_NAME", "goalixa_auth")
    app.config["SKIP_AUTH"] = os.getenv("SKIP_AUTH", "0") == "1"
    # Dual-token authentication configuration
    app.config["AUTH_ACCESS_TOKEN_TTL_MINUTES"] = int(os.getenv("AUTH_ACCESS_TOKEN_TTL_MINUTES", "15"))
    app.config["AUTH_REFRESH_TOKEN_TTL_DAYS"] = int(os.getenv("AUTH_REFRESH_TOKEN_TTL_DAYS", "7"))
    app.config["AUTH_ACCESS_COOKIE_NAME"] = os.getenv("AUTH_ACCESS_COOKIE_NAME", "goalixa_access")
    app.config["AUTH_REFRESH_COOKIE_NAME"] = os.getenv("AUTH_REFRESH_COOKIE_NAME", "goalixa_refresh")
    app.config["AUTH_COOKIE_SAMESITE"] = os.getenv("AUTH_COOKIE_SAMESITE", "Lax")
    app.config["AUTH_COOKIE_SECURE"] = os.getenv("AUTH_COOKIE_SECURE", "0") == "1"
    app.config["AUTH_COOKIE_DOMAIN"] = os.getenv("AUTH_COOKIE_DOMAIN")

    # Respect Cloudflare/forwarded headers for scheme/host/prefix resolution.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    register_observability(app)
    init_auth(app)
    register_auth_routes(app)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set (e.g. postgresql://user:pass@host:5432/db)")
    app.config["DATABASE_URL"] = database_url
    repository = PostgresTaskRepository(database_url)
    service = TaskService(repository)

    register_routes(app, service)
    app.teardown_appcontext(repository.close_db)
    with app.app_context():
        service.init_db()

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "80"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=debug)
