import os

from flask import Flask

from app.auth.models import db, init_security

from app.presentation.filters import register_filters
from app.presentation.routes import register_routes
from app.repository.sqlite_repository import SQLiteTaskRepository
from app.service.task_service import TaskService

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "data.db")


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SECURITY_PASSWORD_SALT"] = os.getenv("SECURITY_PASSWORD_SALT", "dev-salt")
    app.config["SECURITY_REGISTERABLE"] = True
    app.config["SECURITY_SEND_REGISTER_EMAIL"] = False
    app.config["SECURITY_RECOVERABLE"] = True
    app.config["SECURITY_CHANGEABLE"] = True
    app.config["SECURITY_TRACKABLE"] = True
    app.config["SECURITY_CONFIRMABLE"] = False
    app.config["SECURITY_EMAIL_SENDER"] = os.getenv("SECURITY_EMAIL_SENDER", "no-reply@example.com")
    app.config["SECURITY_LOGIN_USER_TEMPLATE"] = "security/login_user.html"
    app.config["SECURITY_REGISTER_USER_TEMPLATE"] = "security/register_user.html"
    app.config["SECURITY_FORGOT_PASSWORD_TEMPLATE"] = "security/forgot_password.html"
    app.config["SECURITY_RESET_PASSWORD_TEMPLATE"] = "security/reset_password.html"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    init_security(app)

    repository = SQLiteTaskRepository(DB_PATH)
    service = TaskService(repository)

    register_routes(app, service)
    register_filters(app)
    app.teardown_appcontext(repository.close_db)

    with app.app_context():
        service.init_db()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
