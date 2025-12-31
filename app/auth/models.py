import os
import uuid
from datetime import datetime

from flask_security import SQLAlchemyUserDatastore, Security, hash_password
from flask_security.models import fsqla_v3 as fsqla
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
fsqla.FsModels.set_db_info(db)


class Role(db.Model, fsqla.FsRoleMixin):
    __tablename__ = "role"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))


class User(db.Model, fsqla.FsUserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean(), default=True)
    confirmed_at = db.Column(db.DateTime())
    fs_uniquifier = db.Column(
        db.String(64), unique=True, nullable=False, default=lambda: uuid.uuid4().hex
    )
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    roles = db.relationship(
        "Role", secondary=fsqla.FsModels.roles_users, backref="users"
    )


def init_security(app):
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security = Security(app, user_datastore)

    with app.app_context():
        db.create_all()
        admin_email = os.getenv("ADMIN_EMAIL")
        admin_password = os.getenv("ADMIN_PASSWORD")
        if admin_email and admin_password:
            if not user_datastore.find_user(email=admin_email):
                admin_role = user_datastore.find_or_create_role(
                    name="admin", description="Administrator"
                )
                user = user_datastore.create_user(
                    email=admin_email,
                    password=hash_password(admin_password),
                )
                user_datastore.add_role_to_user(user, admin_role)
                db.session.commit()

    return security
