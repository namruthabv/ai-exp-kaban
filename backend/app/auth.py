import base64
import hashlib
import hmac
import os
import secrets


SESSION_COOKIE = "pm_session"
SESSION_SECRET_ENV = "SESSION_SECRET"
MVP_USERNAME = "user"
MVP_PASSWORD = "password"


def get_session_secret(configured_secret: str | None = None) -> bytes:
    secret = configured_secret or os.getenv(SESSION_SECRET_ENV)
    return secret.encode() if secret else secrets.token_bytes(32)


def create_session_token(username: str, secret: bytes) -> str:
    payload = base64.urlsafe_b64encode(username.encode()).decode().rstrip("=")
    signature = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def read_session_token(token: str | None, secret: bytes) -> str | None:
    if not token:
        return None

    try:
        payload, signature = token.split(".", maxsplit=1)
        expected = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        padding = "=" * (-len(payload) % 4)
        return base64.urlsafe_b64decode(payload + padding).decode()
    except (UnicodeDecodeError, ValueError):
        return None
