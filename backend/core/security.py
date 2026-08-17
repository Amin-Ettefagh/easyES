"""Field-level encryption helpers for storing secrets (API credentials).

Secrets are encrypted at rest with Fernet (AES-128-CBC + HMAC). The key comes
from ``settings.ENCRYPTION_KEY``. In development, if no key is configured we
derive a stable key from ``SECRET_KEY`` so the demo runs without extra setup —
this is explicitly NOT secure and production must set EASYES_ENCRYPTION_KEY.

Nothing in this module ever logs plaintext secrets.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _derive_key() -> bytes:
    configured = getattr(settings, "ENCRYPTION_KEY", "") or ""
    if configured:
        # Accept either a raw Fernet key or arbitrary passphrase.
        try:
            Fernet(configured.encode())
            return configured.encode()
        except (ValueError, TypeError):
            digest = hashlib.sha256(configured.encode()).digest()
            return base64.urlsafe_b64encode(digest)
    # Dev fallback derived from SECRET_KEY (insecure, deterministic).
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet:
    return Fernet(_derive_key())


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext secret, returning a URL-safe token string."""
    if plaintext is None:
        plaintext = ""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a token produced by :func:`encrypt`. Returns "" on failure."""
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return ""


def mask(secret: str, visible: int = 4) -> str:
    """Return a masked representation safe for display/logging."""
    if not secret:
        return ""
    if len(secret) <= visible:
        return "*" * len(secret)
    return f"{'*' * (len(secret) - visible)}{secret[-visible:]}"


# Domain-facing aliases. Models import these names to make intent explicit at
# the call site (``encrypt_secret`` reads better on a Credential than ``encrypt``).
encrypt_secret = encrypt
decrypt_secret = decrypt
