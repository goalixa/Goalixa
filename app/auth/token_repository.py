import logging
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import dict_row


logger = logging.getLogger(__name__)


class RefreshTokenRepository:
    """PostgreSQL repository for refresh token management."""

    def __init__(self, database_url):
        self.database_url = database_url

    def _get_db(self, g=None):
        """Get database connection from Flask g object or create new one."""
        if g and "db" in g:
            return g.db
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def create_refresh_token(self, user_id, token_str, expires_at, g=None):
        """Create a new refresh token in the database."""
        db = self._get_db(g)
        cursor = db.execute(
            """
            INSERT INTO refresh_token (token, token_id, user_id, expires_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (token_str, token_str, user_id, expires_at),
        )
        row = cursor.fetchone()
        db.commit()
        logger.info("refresh token created", extra={"token_id": token_str, "user_id": user_id})
        return row["id"] if row else None

    def get_refresh_token(self, token_id, user_id, g=None):
        """Retrieve a refresh token by token_id and user_id."""
        db = self._get_db(g)
        row = db.execute(
            """
            SELECT id, token, token_id, user_id, expires_at, created_at, revoked_at, replaced_by
            FROM refresh_token
            WHERE token_id = %s AND user_id = %s
            """,
            (token_id, user_id),
        ).fetchone()
        return row

    def revoke_refresh_token(self, token_id, g=None):
        """Mark a refresh token as revoked."""
        db = self._get_db(g)
        db.execute(
            "UPDATE refresh_token SET revoked_at = %s WHERE token_id = %s",
            (datetime.utcnow(), token_id),
        )
        db.commit()
        logger.info("refresh token revoked", extra={"token_id": token_id})

    def revoke_all_user_tokens(self, user_id, g=None):
        """Revoke all active refresh tokens for a user."""
        db = self._get_db(g)
        cursor = db.execute(
            "UPDATE refresh_token SET revoked_at = %s WHERE user_id = %s AND revoked_at IS NULL",
            (datetime.utcnow(), user_id),
        )
        count = cursor.rowcount
        db.commit()
        logger.info("all user tokens revoked", extra={"user_id": user_id, "count": count})
        return count

    def is_token_valid(self, token_id, user_id, g=None):
        """Check if a token is valid (not expired and not revoked)."""
        db = self._get_db(g)
        row = db.execute(
            """
            SELECT id, expires_at, revoked_at
            FROM refresh_token
            WHERE token_id = %s AND user_id = %s
            """,
            (token_id, user_id),
        ).fetchone()

        if not row:
            return False

        # Check if revoked
        if row["revoked_at"] is not None:
            return False

        # Check if expired
        if isinstance(row["expires_at"], str):
            expires_at = datetime.fromisoformat(row["expires_at"])
        else:
            expires_at = row["expires_at"]

        return expires_at >= datetime.utcnow()

    def rotate_refresh_token(self, old_token_id, new_token_str, user_id, expires_at, g=None):
        """
        Rotate a refresh token: create new one and mark old as revoked.
        Returns the new token ID.
        """
        db = self._get_db(g)

        # Create new refresh token
        cursor = db.execute(
            """
            INSERT INTO refresh_token (token, token_id, user_id, expires_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (new_token_str, new_token_str, user_id, expires_at),
        )
        new_row = cursor.fetchone()
        new_id = new_row["id"] if new_row else None

        if new_id:
            # Revoke old token and set replaced_by
            db.execute(
                """
                UPDATE refresh_token
                SET revoked_at = %s, replaced_by = %s
                WHERE token_id = %s
                """,
                (datetime.utcnow(), new_id, old_token_id),
            )

        db.commit()
        logger.info(
            "refresh token rotated",
            extra={"old_token_id": old_token_id, "new_token_id": new_token_str, "user_id": user_id},
        )
        return new_id

    def ensure_user_exists(self, user_id, email, g=None):
        """Ensure user exists in the database. Create if not exists."""
        db = self._get_db(g)

        # Check if user exists
        row = db.execute('SELECT id FROM "user" WHERE id = %s', (user_id,)).fetchone()
        if row:
            return user_id

        # Create user with placeholder values
        db.execute(
            """
            INSERT INTO "user" (id, email, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (user_id, email, datetime.utcnow().isoformat()),
        )
        db.commit()
        logger.info("user created in app db", extra={"user_id": user_id, "email": email})
        return user_id
