import jwt
from functools import wraps
from urllib.parse import urlencode

from flask import current_app, g, jsonify, redirect, request
from werkzeug.local import LocalProxy


class AuthUser:
    def __init__(self, user_id=None, email=""):
        self.id = user_id
        self.email = email
        self.is_authenticated = user_id is not None


class AnonymousUser(AuthUser):
    def __init__(self):
        super().__init__(user_id=None, email="")


current_user = LocalProxy(lambda: getattr(g, "auth_user", AnonymousUser()))


def _auth_settings():
    base_url = current_app.config.get("AUTH_SERVICE_URL", "https://goalixa.com/auth").rstrip("/")
    cookie_name = current_app.config.get("AUTH_COOKIE_NAME", "goalixa_auth")
    secret = current_app.config.get("AUTH_JWT_SECRET", "dev-jwt-secret")
    return base_url, cookie_name, secret


def _decode_token(token, secret):
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        return None
    return payload


def _load_user_from_request():
    _, cookie_name, secret = _auth_settings()
    token = request.cookies.get(cookie_name)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return AnonymousUser()
    payload = _decode_token(token, secret)
    if not payload:
        return AnonymousUser()
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return AnonymousUser()
    return AuthUser(user_id=user_id, email=payload.get("email", ""))


def init_auth(app):
    @app.before_request
    def load_auth_user():
        # Check if auth should be skipped for local development
        skip_auth = app.config.get("SKIP_AUTH", False)
        if skip_auth:
            # Create a fake dev user for local development
            g.auth_user = AuthUser(user_id=1, email="dev@localhost")
        else:
            g.auth_user = _load_user_from_request()

    app.jinja_env.globals["url_for_security"] = url_for_security


def url_for_security(endpoint, **values):
    base_url, _, _ = _auth_settings()
    route_map = {
        "login": "/login",
        "register": "/register",
        "forgot_password": "/forgot",
        "reset_password": "/reset/{token}",
        "change_password": "/change-password",
        "logout": "/logout",
        "profile": "/change-password",
    }
    path = route_map.get(endpoint)
    if not path:
        raise ValueError(f"Unknown auth endpoint: {endpoint}")
    if "{token}" in path:
        token = values.pop("token", "")
        path = path.format(token=token)
    query = {}
    next_url = values.pop("next", None)
    if next_url:
        query["next"] = next_url
    if values:
        query.update(values)
    if query:
        return f"{base_url}{path}?{urlencode(query)}"
    return f"{base_url}{path}"


def auth_required():
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Skip auth check if SKIP_AUTH is enabled
            skip_auth = current_app.config.get("SKIP_AUTH", False)
            if skip_auth or current_user.is_authenticated:
                return func(*args, **kwargs)
            if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
                return jsonify({"error": "unauthorized"}), 401
            # Force HTTPS in the redirect URL to prevent redirect loops
            next_url = request.url
            if next_url.startswith("http://"):
                next_url = next_url.replace("http://", "https://", 1)
            return redirect(url_for_security("login", next=next_url))

        return wrapper

    return decorator
