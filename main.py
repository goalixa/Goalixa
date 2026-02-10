import os
import time

from dotenv import load_dotenv

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.auth_client import init_auth

from app.presentation.filters import register_filters
from app.presentation.routes import register_routes
from app.repository.postgres_repository import PostgresTaskRepository
from app.service.task_service import TaskService

def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["AUTH_SERVICE_URL"] = os.getenv(
        "AUTH_SERVICE_URL",
        "https://goalixa.com/auth",
    )
    app.config["AUTH_JWT_SECRET"] = os.getenv("AUTH_JWT_SECRET", "dev-jwt-secret")
    app.config["AUTH_COOKIE_NAME"] = os.getenv("AUTH_COOKIE_NAME", "goalixa_auth")
    app.config["SKIP_AUTH"] = os.getenv("SKIP_AUTH", "0") == "1"
    app.config["DEMO_SEED_KEY"] = os.getenv("DEMO_SEED_KEY", "")
    app.config["DEMO_MODE_ENABLED"] = os.getenv("DEMO_MODE_ENABLED", "0") == "1"
    demo_user_id = os.getenv("DEMO_USER_ID")
    app.config["DEMO_USER_ID"] = int(demo_user_id) if demo_user_id else None

    # Cache-busting for CSS - changes on each server restart
    app.config["CSS_VERSION"] = str(int(time.time()))

    # Respect Cloudflare/forwarded headers for scheme/host/prefix resolution.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    init_auth(app)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set (e.g. postgresql://user:pass@host:5432/db)")
    repository = PostgresTaskRepository(database_url)
    service = TaskService(repository)

    register_routes(app, service)
    register_filters(app)
    app.teardown_appcontext(repository.close_db)
    with app.app_context():
        service.init_db()

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "80"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=debug)
