import os

from dotenv import load_dotenv

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.auth_client import init_auth

from app.presentation.filters import register_filters
from app.presentation.routes import register_routes
from app.repository.sqlite_repository import SQLiteTaskRepository
from app.service.task_service import TaskService

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "data.db")


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

    # Respect Cloudflare/forwarded headers for scheme/host resolution.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    init_auth(app)

    repository = SQLiteTaskRepository(DB_PATH)
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
