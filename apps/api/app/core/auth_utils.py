"""
Authentication utilities for source connectors.
Supports cookie, bearer token, API key, and custom headers.
"""
import base64
import hashlib
import json
import os
from typing import Literal

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Auth types supported
AuthType = Literal["none", "cookie", "bearer", "api_key", "custom_headers"]

# Default encryption key (should be overridden in production)
_DEFAULT_KEY = "daily-headlines-default-key-change-me"


def _get_encryption_key() -> bytes:
    """Get or generate encryption key from environment."""
    secret = os.getenv("AUTH_SECRET_KEY", _DEFAULT_KEY)
    # Derive a proper Fernet key from the secret
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"daily-headlines-auth-salt",
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return key


def encrypt_value(value: str) -> str:
    """Encrypt a sensitive value for storage."""
    if not value:
        return ""
    key = _get_encryption_key()
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    """Decrypt a stored sensitive value."""
    if not encrypted:
        return ""
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        # If decryption fails, return empty (might be plaintext legacy data)
        return ""


def build_auth_headers(auth_type: str, auth_config: dict) -> dict[str, str]:
    """Build HTTP headers from auth configuration."""
    if auth_type == "none" or not auth_config:
        return {}

    headers = {}

    if auth_type == "cookie":
        cookies = auth_config.get("cookies", "")
        if cookies:
            # Decrypt if encrypted
            if auth_config.get("encrypted"):
                cookies = decrypt_value(cookies)
            headers["Cookie"] = cookies

    elif auth_type == "bearer":
        token = auth_config.get("token", "")
        if token:
            if auth_config.get("encrypted"):
                token = decrypt_value(token)
            headers["Authorization"] = f"Bearer {token}"

    elif auth_type == "api_key":
        header_name = auth_config.get("header_name", "X-API-Key")
        api_key = auth_config.get("api_key", "")
        if api_key:
            if auth_config.get("encrypted"):
                api_key = decrypt_value(api_key)
            headers[header_name] = api_key

    elif auth_type == "custom_headers":
        custom = auth_config.get("headers", {})
        for key, value in custom.items():
            if isinstance(value, str):
                headers[key] = value

    return headers


def prepare_auth_for_storage(auth_type: str, auth_config: dict) -> dict:
    """Prepare auth config for storage (encrypt sensitive fields)."""
    if auth_type == "none" or not auth_config:
        return {"auth_type": "none", "auth_config": {}}

    config = auth_config.copy()
    config["encrypted"] = True

    if auth_type == "cookie":
        cookies = config.get("cookies", "")
        if cookies and not config.get("encrypted"):
            config["cookies"] = encrypt_value(cookies)

    elif auth_type == "bearer":
        token = config.get("token", "")
        if token and not config.get("encrypted"):
            config["token"] = encrypt_value(token)

    elif auth_type == "api_key":
        api_key = config.get("api_key", "")
        if api_key and not config.get("encrypted"):
            config["api_key"] = encrypt_value(api_key)

    return {"auth_type": auth_type, "auth_config": config}


def mask_auth_config(auth_type: str, auth_config: dict) -> dict:
    """Mask sensitive fields for API response (don't expose actual values)."""
    if auth_type == "none" or not auth_config:
        return {"auth_type": "none", "auth_config": {}}

    config = auth_config.copy()

    if auth_type == "cookie":
        cookies = config.get("cookies", "")
        if cookies:
            config["cookies"] = "••••••••"
        config["has_cookies"] = bool(cookies)

    elif auth_type == "bearer":
        token = config.get("token", "")
        if token:
            config["token"] = "••••••••"
        config["has_token"] = bool(token)

    elif auth_type == "api_key":
        api_key = config.get("api_key", "")
        if api_key:
            config["api_key"] = "••••••••"
        config["has_api_key"] = bool(api_key)

    # Remove encrypted flag from response
    config.pop("encrypted", None)

    return {"auth_type": auth_type, "auth_config": config}
