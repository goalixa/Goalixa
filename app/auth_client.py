import jwt
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlencode

from flask import current_app, g, jsonify, redirect, request
from werkzeug.local import LocalProxy

from app.auth.jwt import (
    create_access_token,
    create_refresh_token_jwt,
    create_refresh_token_string,
    decode_access_token,
    decode_refresh_token,
)


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
    access_cookie_name = current_app.config.get("AUTH_ACCESS_COOKIE_NAME", "goalixa_access")
    refresh_cookie_name = current_app.config.get("AUTH_REFRESH_COOKIE_NAME", "goalixa_refresh")
    secret = current_app.config.get("AUTH_JWT_SECRET", "dev-jwt-secret")
    access_ttl = current_app.config.get("AUTH_ACCESS_TOKEN_TTL_MINUTES", 15)
    refresh_ttl = current_app.config.get("AUTH_REFRESH_TOKEN_TTL_DAYS", 7)
    # Convert string "None" to Python None for Flask's set_cookie()
    # Flask needs None (not "None") to set SameSite=None correctly
    # Use 'Lax' by default for better browser compatibility
    samesite_config = current_app.config.get("AUTH_COOKIE_SAMESITE", "Lax")
    samesite = None if samesite_config == "None" else samesite_config
    return base_url, access_cookie_name, refresh_cookie_name, secret, access_ttl, refresh_ttl, samesite, current_app.config.get("AUTH_COOKIE_DOMAIN"), current_app.config.get("AUTH_COOKIE_SECURE", True)


def _decode_token(token, secret):
    """Legacy function - decodes old single-token format."""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        return None
    return payload


def _load_user_from_request():
    """
    Load user from dual-token cookies.
    1. Try access token first
    2. If access token invalid, try refresh token and auto-issue new access token
    3. Fall back to legacy single-token format for backward compatibility
    """
    _, access_cookie_name, refresh_cookie_name, secret, access_ttl, refresh_ttl, _, _, _ = _auth_settings()

    # Try access token first (new dual-token system)
    access_token = request.cookies.get(access_cookie_name)
    if access_token:
        payload, err = decode_access_token(access_token, secret)
        if not err and payload and "sub" in payload:
            try:
                user_id = int(payload.get("sub"))
            except (TypeError, ValueError):
                pass
            else:
                return AuthUser(user_id=user_id, email=payload.get("email", ""))

    # Access token missing or invalid, try refresh token
    refresh_token = request.cookies.get(refresh_cookie_name)
    if refresh_token:
        payload, err = decode_refresh_token(refresh_token, secret)
        if not err and payload and "sub" in payload and "jti" in payload:
            try:
                user_id = int(payload.get("sub"))
            except (TypeError, ValueError):
                pass
            else:
                # Check if refresh token is valid in database
                from app.auth.token_repository import RefreshTokenRepository

                token_repo = RefreshTokenRepository(current_app.config.get("DATABASE_URL"))
                if token_repo.is_token_valid(payload["jti"], user_id):
                    # Auto-issue new access token and rotate refresh token
                    new_access_token = create_access_token(
                        user_id=user_id,
                        email=payload.get("email", ""),
                        secret=secret,
                        ttl_minutes=access_ttl,
                    )

                    # Rotate refresh token: create new one and revoke old
                    from datetime import datetime, timedelta
                    new_refresh_token_str = create_refresh_token_string()
                    new_refresh_token_jwt = create_refresh_token_jwt(
                        user_id=user_id,
                        token_id=new_refresh_token_str,
                        secret=secret,
                        ttl_days=refresh_ttl,
                    )

                    new_refresh_expires = datetime.utcnow() + timedelta(days=refresh_ttl)
                    token_repo.rotate_refresh_token(
                        old_token_id=payload["jti"],
                        new_token_str=new_refresh_token_str,
                        user_id=user_id,
                        expires_at=new_refresh_expires,
                        g=g,
                    )

                    # Signal to set new access AND refresh token cookies in after_request
                    g.new_access_token = new_access_token
                    g.new_refresh_token = new_refresh_token_jwt
                    return AuthUser(user_id=user_id, email=payload.get("email", ""))

    # Fall back to legacy single-token format for backward compatibility
    legacy_cookie_name = current_app.config.get("AUTH_COOKIE_NAME", "goalixa_auth")
    legacy_token = request.cookies.get(legacy_cookie_name)
    if legacy_token:
        # Check Authorization header too
        if not legacy_token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                legacy_token = auth_header.split(" ", 1)[1].strip()
        if legacy_token:
            payload = _decode_token(legacy_token, secret)
            if payload:
                try:
                    user_id = int(payload.get("sub"))
                except (TypeError, ValueError):
                    pass
                else:
                    return AuthUser(user_id=user_id, email=payload.get("email", ""))

    # Also check Authorization header for access/refresh tokens
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        bearer_token = auth_header.split(" ", 1)[1].strip()
        # Try as access token
        payload, err = decode_access_token(bearer_token, secret)
        if not err and payload and "sub" in payload:
            try:
                user_id = int(payload.get("sub"))
            except (TypeError, ValueError):
                pass
            else:
                return AuthUser(user_id=user_id, email=payload.get("email", ""))

    return AnonymousUser()


def init_auth(app):
    @app.before_request
    def load_auth_user():
        # Check if auth should be skipped for local development
        skip_auth = app.config.get("SKIP_AUTH", False)
        demo_enabled = app.config.get("DEMO_MODE_ENABLED", False)
        demo_user_id = app.config.get("DEMO_USER_ID")
        demo_cookie = request.cookies.get("goalixa_demo") == "1"
        if demo_enabled and demo_cookie and demo_user_id:
            g.auth_user = AuthUser(user_id=demo_user_id, email="demo@goalixa.local")
            g.demo_mode = True
        elif skip_auth and not demo_enabled:
            # Create a fake dev user for local development
            g.auth_user = AuthUser(user_id=1, email="dev@localhost")
            g.demo_mode = False
        else:
            g.auth_user = _load_user_from_request()
            g.demo_mode = False

    @app.after_request
    def set_new_tokens(response):
        """Set new access and/or refresh token cookies if they were auto-refreshed."""
        _, access_cookie_name, refresh_cookie_name, _, access_ttl, refresh_ttl, samesite, cookie_domain, cookie_secure = _auth_settings()

        if hasattr(g, "new_access_token"):
            response.set_cookie(
                access_cookie_name,
                g.new_access_token,
                max_age=access_ttl * 60,
                httponly=True,
                samesite=samesite,
                secure=cookie_secure,
                path="/",
                domain=cookie_domain,
            )

        if hasattr(g, "new_refresh_token"):
            response.set_cookie(
                refresh_cookie_name,
                g.new_refresh_token,
                max_age=refresh_ttl * 86400,
                httponly=True,
                samesite=samesite,
                secure=cookie_secure,
                path="/",
                domain=cookie_domain,
            )
        return response

    app.jinja_env.globals["url_for_security"] = url_for_security


def url_for_security(endpoint, **values):
    """Generate URL for security endpoints."""
    base_url = (current_app.config.get("AUTH_SERVICE_URL") or "").rstrip("/")
    if base_url:
        # External auth service UI routes (browser-friendly GET/POST pages)
        route_map = {
            "login": "/login",
            "register": "/register",
            "forgot_password": "/forgot",
            "reset_password": "/reset/{token}",
            "change_password": "/change-password",
            "logout": "/logout",
            "profile": "/change-password",
        }
    else:
        # Local API routes (useful for dev/test or programmatic login)
        route_map = {
            "login": "/api/auth/login",
            "register": "/api/auth/register",
            "forgot_password": "/api/auth/forgot",
            "reset_password": "/api/auth/reset/{token}",
            "change_password": "/api/auth/change-password",
            "logout": "/api/auth/logout",
            "profile": "/api/auth/change-password",
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
            demo_enabled = current_app.config.get("DEMO_MODE_ENABLED", False)
            if (skip_auth and not demo_enabled) or current_user.is_authenticated:
                return func(*args, **kwargs)
            if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
                return jsonify({"error": "unauthorized"}), 401
            # Redirect to /demo if demo mode is enabled
            if demo_enabled:
                return redirect("/demo")
            # Force HTTPS in the redirect URL to prevent redirect loops
            next_url = request.url
            if next_url.startswith("http://"):
                next_url = next_url.replace("http://", "https://", 1)
            return redirect(url_for_security("login", next=next_url))

        return wrapper

    return decorator


def issue_auth_response(user, next_url=None):
    """
    Issue auth response with access and refresh tokens set as cookies.
    Returns a response (either redirect or JSON).
    """
    _, access_cookie_name, refresh_cookie_name, secret, access_ttl, refresh_ttl, samesite, cookie_domain, cookie_secure = _auth_settings()

    # Create access token
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        secret=secret,
        ttl_minutes=access_ttl,
    )

    # Create refresh token
    from app.auth.token_repository import RefreshTokenRepository

    token_repo = RefreshTokenRepository(current_app.config.get("DATABASE_URL"))

    # Ensure user exists in app database
    token_repo.ensure_user_exists(user.id, user.email, g)

    refresh_token_str = create_refresh_token_string()
    refresh_token_jwt = create_refresh_token_jwt(
        user_id=user.id,
        token_id=refresh_token_str,
        secret=secret,
        ttl_days=refresh_ttl,
    )

    # Store refresh token in database
    refresh_expires = datetime.utcnow() + timedelta(days=refresh_ttl)
    token_repo.create_refresh_token(user.id, refresh_token_str, refresh_expires, g)

    # Determine response type based on request
    if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
        from flask import make_response

        response = make_response({"success": True, "user": {"email": user.email}})
        response.set_cookie(
            access_cookie_name,
            access_token,
            max_age=access_ttl * 60,
            httponly=True,
            samesite=samesite,
            secure=cookie_secure,
            path="/",
            domain=cookie_domain,
        )
        response.set_cookie(
            refresh_cookie_name,
            refresh_token_jwt,
            max_age=refresh_ttl * 86400,
            httponly=True,
            samesite=samesite,
            secure=cookie_secure,
            path="/",
            domain=cookie_domain,
        )
        return response

    # Web redirect response
    from flask import make_response, redirect

    target = next_url or "/"
    response = make_response(redirect(target))
    response.set_cookie(
        access_cookie_name,
        access_token,
        max_age=access_ttl * 60,
        httponly=True,
        samesite=samesite,
        secure=cookie_secure,
        path="/",
        domain=cookie_domain,
    )
    response.set_cookie(
        refresh_cookie_name,
        refresh_token_jwt,
        max_age=refresh_ttl * 86400,
        httponly=True,
        samesite=samesite,
        secure=cookie_secure,
        path="/",
        domain=cookie_domain,
    )
    return response


def clear_auth_cookies():
    """Clear both access and refresh cookies."""
    from flask import make_response

    _, access_cookie_name, refresh_cookie_name, _, _, _, samesite, cookie_domain, _ = _auth_settings()

    response = make_response()

    # Clear access cookie
    response.delete_cookie(
        access_cookie_name,
        path="/",
        domain=cookie_domain,
        samesite=samesite,
    )

    # Clear refresh cookie
    response.delete_cookie(
        refresh_cookie_name,
        path="/",
        domain=cookie_domain,
        samesite=samesite,
    )

    # Also clear legacy cookie
    legacy_cookie_name = current_app.config.get("AUTH_COOKIE_NAME", "goalixa_auth")
    response.delete_cookie(
        legacy_cookie_name,
        path="/",
        domain=cookie_domain,
        samesite=samesite,
    )

    return response
