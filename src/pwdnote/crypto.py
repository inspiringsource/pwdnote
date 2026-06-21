"""Crypto abstraction layer.

This module isolates all cryptographic details behind a tiny interface so the
backend can be swapped later without touching the rest of the codebase.

Current backend: Fernet (AES-128-CBC + HMAC-SHA256) from the ``cryptography``
library, which provides authenticated, integrity-protected encryption with a
versioned token format. We intentionally do NOT implement custom cryptography.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


class DecryptionError(Exception):
    """Raised when a note cannot be decrypted (wrong key or corrupted data)."""


def generate_key() -> bytes:
    """Generate a fresh, URL-safe base64-encoded encryption key."""
    return Fernet.generate_key()


def _fernet(key: bytes) -> Fernet:
    try:
        return Fernet(key)
    except (ValueError, TypeError) as exc:
        raise DecryptionError("Invalid encryption key.") from exc


def encrypt_text(plaintext: str, key: bytes) -> bytes:
    """Encrypt ``plaintext`` and return an opaque, integrity-protected token."""
    return _fernet(key).encrypt(plaintext.encode("utf-8"))


def decrypt_text(token: bytes, key: bytes) -> str:
    """Decrypt and authenticate ``token``, returning the original text.

    Raises:
        DecryptionError: if the key is wrong, the key is malformed, or the
            token has been tampered with / corrupted.
    """
    try:
        return _fernet(key).decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        raise DecryptionError("Unable to decrypt project note.") from exc
