import os

from dotenv import load_dotenv

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.auth.models import db, init_security
from app.auth.oauth import init_oauth

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
    app.config["SECURITY_PASSWORD_SALT"] = os.getenv("SECURITY_PASSWORD_SALT", "dev-salt")
    app.config["SECURITY_REGISTERABLE"] = True
    app.config["SECURITY_SEND_REGISTER_EMAIL"] = False
    app.config["SECURITY_RECOVERABLE"] = True
    app.config["SECURITY_CHANGEABLE"] = True
    app.config["SECURITY_TRACKABLE"] = True
    app.config["SECURITY_CONFIRMABLE"] = False
    app.config["SECURITY_PROFILEABLE"] = True
    app.config["SECURITY_PASSWORD_HASH"] = "pbkdf2_sha512"
    app.config["SECURITY_PASSWORD_SCHEMES"] = ["pbkdf2_sha512"]
    app.config["SECURITY_EMAIL_SENDER"] = os.getenv("SECURITY_EMAIL_SENDER", "no-reply@example.com")
    app.config["SECURITY_LOGIN_USER_TEMPLATE"] = "security/login_user.html"
    app.config["SECURITY_REGISTER_USER_TEMPLATE"] = "security/register_user.html"
    app.config["SECURITY_FORGOT_PASSWORD_TEMPLATE"] = "security/forgot_password.html"
    app.config["SECURITY_RESET_PASSWORD_TEMPLATE"] = "security/reset_password.html"
    app.config["SECURITY_PROFILE_USER_TEMPLATE"] = "security/profile.html"
    app.config["SECURITY_CHANGE_PASSWORD_TEMPLATE"] = "security/change_password.html"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Respect Cloudflare/forwarded headers for scheme/host resolution.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    init_security(app)
    init_oauth(app)

    repository = SQLiteTaskRepository(DB_PATH)
    service = TaskService(repository)

    register_routes(app, service)
    register_filters(app)
    app.teardown_appcontext(repository.close_db)
    app.context_processor(lambda: {
        "google_oauth_enabled": app.config.get("GOOGLE_OAUTH_ENABLED", False),
    })

    with app.app_context():
        service.init_db()

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "80"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=debug)
