import logging
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, g, jsonify, make_response, request
from werkzeug.security import check_password_hash, generate_password_hash

from app.auth.jwt import (
    create_access_token,
    create_refresh_token_jwt,
    create_refresh_token_string,
    decode_access_token,
    decode_refresh_token,
)
from app.auth.token_repository import RefreshTokenRepository


logger = logging.getLogger(__name__)

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def register_auth_routes(app):
    """Register authentication routes with the Flask app."""
    app.register_blueprint(bp)


@bp.route("/login", methods=["POST"])
def api_login():
    """Handle login - issue access and refresh tokens."""
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    if not email or not password:
        logger.warning("api login missing credentials")
        return jsonify({"success": False, "error": "Email and password are required."}), 400

    # Get database connection and check user
    from app.auth_client import issue_auth_response

    # For now, we'll accept any login and create a user on-the-fly
    # This should be replaced with proper password verification
    # using the auth service or local user table
    from app.auth_client import AuthUser

    # Create a mock user - in production, validate against auth service
    user = AuthUser(user_id=1, email=email)  # Placeholder user

    logger.info("api login success", extra={"email": email})
    return issue_auth_response(user)


@bp.route("/register", methods=["POST"])
def api_register():
    """Handle registration - create user and issue tokens."""
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    if not email or not password:
        logger.warning("api register missing credentials")
        return jsonify({"success": False, "error": "Email and password are required."}), 400

    # For now, we'll accept any registration and create a user on-the-fly
    # This should be replaced with proper user creation logic
    from app.auth_client import issue_auth_response, AuthUser

    # Create a mock user - in production, create user in database
    import hashlib
    import time

    user_id = int(hashlib.md5(email.encode()).hexdigest()[:8], 16) % 1000000
    user = AuthUser(user_id=user_id, email=email)

    logger.info("api register success", extra={"user_id": user_id, "email": email})
    return issue_auth_response(user)


@bp.route("/refresh", methods=["POST"])
def api_refresh():
    """Exchange refresh token for new access token (with rotation)."""
    _, refresh_cookie_name, _, secret, access_ttl, refresh_ttl = _get_auth_settings()
    refresh_token_jwt = request.cookies.get(refresh_cookie_name)

    if not refresh_token_jwt:
        logger.warning("api refresh missing cookie")
        return jsonify({"success": False, "error": "Refresh token not found."}), 401

    # Decode refresh token JWT
    payload, err = decode_refresh_token(refresh_token_jwt, secret)
    if err:
        logger.warning("api refresh decode failed", extra={"reason": err})
        return jsonify({"success": False, "error": "Invalid refresh token."}), 401

    if not payload or "sub" not in payload or "jti" not in payload:
        logger.warning("api refresh invalid payload")
        return jsonify({"success": False, "error": "Invalid refresh token."}), 401

    # Check database for token validity
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        logger.warning("api refresh invalid user_id", extra={"sub": payload.get("sub")})
        return jsonify({"success": False, "error": "Invalid refresh token."}), 401

    token_repo = RefreshTokenRepository(current_app.config.get("AUTH_DATABASE_URL", current_app.config.get("DATABASE_URL")))
    refresh_token = token_repo.get_refresh_token(payload["jti"], user_id)

    if not refresh_token or not token_repo.is_token_valid(payload["jti"], user_id):
        logger.warning(
            "api refresh token invalid or revoked",
            extra={"token_id": payload["jti"], "user_id": user_id},
        )
        return jsonify({"success": False, "error": "Invalid or expired refresh token."}), 401

    # Create new access token
    access_token = create_access_token(
        user_id=user_id,
        email=payload.get("email", ""),
        secret=secret,
        ttl_minutes=access_ttl,
    )

    # Rotate refresh token (issue new one, revoke old)
    new_refresh_token_str = create_refresh_token_string()
    new_refresh_token_jwt = create_refresh_token_jwt(
        user_id=user_id,
        token_id=new_refresh_token_str,
        secret=secret,
        ttl_days=refresh_ttl,
    )

    # Create new refresh token record
    new_refresh_expires = datetime.now(timezone.utc) + timedelta(days=refresh_ttl)
    token_repo.rotate_refresh_token(
        old_token_id=payload["jti"],
        new_token_str=new_refresh_token_str,
        user_id=user_id,
        expires_at=new_refresh_expires,
        g=g,
    )

    logger.info(
        "api refresh success",
        extra={
            "user_id": user_id,
            "old_token_id": payload["jti"],
            "new_token_id": new_refresh_token_str,
        },
    )

    # Set new cookies
    cookie_secure = current_app.config.get("AUTH_COOKIE_SECURE", False)
    cookie_samesite = current_app.config.get("AUTH_COOKIE_SAMESITE", "Lax")
    cookie_domain = current_app.config.get("AUTH_COOKIE_DOMAIN")

    response = make_response({"success": True, "access_token": access_token})
    response.set_cookie(
        current_app.config.get("AUTH_ACCESS_COOKIE_NAME", "goalixa_access"),
        access_token,
        max_age=access_ttl * 60,
        httponly=True,
        samesite=cookie_samesite,
        secure=cookie_secure,
        path="/",
        domain=cookie_domain,
    )
    response.set_cookie(
        current_app.config.get("AUTH_REFRESH_COOKIE_NAME", "goalixa_refresh"),
        new_refresh_token_jwt,
        max_age=refresh_ttl * 86400,
        httponly=True,
        samesite=cookie_samesite,
        secure=cookie_secure,
        path="/",
        domain=cookie_domain,
    )

    return response


@bp.route("/logout", methods=["POST"])
def api_logout():
    """Revoke refresh token and clear cookies."""
    _, refresh_cookie_name, _, secret, _, _ = _get_auth_settings()
    refresh_token_jwt = request.cookies.get(refresh_cookie_name)

    if refresh_token_jwt:
        payload, err = decode_refresh_token(refresh_token_jwt, secret)
        if not err and payload and "jti" in payload:
            token_repo = RefreshTokenRepository(current_app.config.get("AUTH_DATABASE_URL", current_app.config.get("DATABASE_URL")))
            token = token_repo.get_refresh_token(payload["jti"], int(payload.get("sub", 0)))
            if token and token.get("revoked_at") is None:
                token_repo.revoke_refresh_token(payload["jti"])
                logger.info("revoked refresh token on logout", extra={"token_id": payload["jti"]})

    logger.info("api logout")

    from app.auth_client import clear_auth_cookies

    response = clear_auth_cookies()
    response.data = jsonify({"success": True}).get_data()
    response.content_type = "application/json"
    return response


@bp.route("/me", methods=["GET"])
def api_me():
    """Get current authenticated user info."""
    from app.auth_client import current_user

    if current_user.is_authenticated:
        return {
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "email": current_user.email,
            },
        }
    return {"authenticated": False, "user": None}


def _get_auth_settings():
    """Helper to get auth settings."""
    return (
        current_app.config.get("AUTH_SERVICE_URL", "https://goalixa.com/auth").rstrip("/"),
        current_app.config.get("AUTH_ACCESS_COOKIE_NAME", "goalixa_access"),
        current_app.config.get("AUTH_REFRESH_COOKIE_NAME", "goalixa_refresh"),
        current_app.config.get("AUTH_JWT_SECRET", "dev-jwt-secret"),
        current_app.config.get("AUTH_ACCESS_TOKEN_TTL_MINUTES", 15),
        current_app.config.get("AUTH_REFRESH_TOKEN_TTL_DAYS", 7),
    )
