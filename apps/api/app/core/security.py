"""Startup security validation — warns or fails on unsafe configurations."""

from __future__ import annotations

import logging
import os
import sys

from app.core.config import settings

logger = logging.getLogger(__name__)

_INSECURE_SECRETS = {
    "dev-secret-change-in-production",
    "secret",
    "password",
    "changeme",
    "",
}

_INSECURE_PASSWORDS = {
    "admin123",
    "admin",
    "password",
    "123456",
    "changeme",
    "",
}


def validate_security_config(*, strict: bool = False) -> list[str]:
    """Validate security-related settings on startup.

    Args:
        strict: If True, insecure configs will cause sys.exit(1).
                If False (default), only log warnings.

    Returns:
        List of warning messages.
    """
    warnings: list[str] = []

    # --- JWT Secret ---
    if settings.jwt_secret in _INSECURE_SECRETS:
        msg = (
            "⚠️  JWT_SECRET is using an insecure default value. "
            "Set a strong random secret via the JWT_SECRET environment variable."
        )
        warnings.append(msg)

    # --- Dev admin password ---
    if settings.dev_admin_password in _INSECURE_PASSWORDS:
        msg = (
            "⚠️  DEV_ADMIN_PASSWORD is using an insecure default value. "
            "Change it via the DEV_ADMIN_PASSWORD environment variable."
        )
        warnings.append(msg)

    # --- CORS origins wildcard ---
    if "*" in settings.cors_origins:
        msg = (
            "⚠️  CORS_ORIGINS includes '*' — this allows any origin. "
            "Restrict to specific domains in production."
        )
        warnings.append(msg)

    # --- Running as root ---
    if hasattr(os, "getuid") and os.getuid() == 0:
        msg = "⚠️  Running as root. Use a non-root user in production."
        warnings.append(msg)

    # --- Database URL check ---
    if settings.database_url.startswith("sqlite") and not os.getenv("DATABASE_URL"):
        msg = (
            "ℹ️  Using SQLite (default). For production, consider MySQL: "
            "DATABASE_URL=mysql+pymysql://user:pass@host/db"
        )
        warnings.append(msg)

    # --- Log all warnings ---
    for w in warnings:
        logger.warning(w)

    if strict and warnings:
        logger.critical("Security validation failed in strict mode. Exiting.")
        sys.exit(1)

    return warnings
