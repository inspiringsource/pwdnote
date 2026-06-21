import pytest

from pwdnote.crypto import (
    DecryptionError,
    decrypt_text,
    encrypt_text,
    generate_key,
)


def test_roundtrip(key):
    token = encrypt_text("hello world", key)
    assert decrypt_text(token, key) == "hello world"


def test_unicode_roundtrip(key):
    text = "déjà vu — 🔐 — TODO"
    assert decrypt_text(encrypt_text(text, key), key) == text


def test_token_is_not_plaintext(key):
    token = encrypt_text("topsecret", key)
    assert b"topsecret" not in token


def test_invalid_key(key):
    token = encrypt_text("hi", key)
    other_key = generate_key()
    with pytest.raises(DecryptionError):
        decrypt_text(token, other_key)


def test_corrupted_file(key):
    token = encrypt_text("hi", key)
    corrupted = token[:-4] + b"AAAA"
    with pytest.raises(DecryptionError):
        decrypt_text(corrupted, key)


def test_malformed_key_raises_decryption_error():
    with pytest.raises(DecryptionError):
        decrypt_text(b"anything", b"not-a-valid-fernet-key")


def test_generate_key_is_unique():
    assert generate_key() != generate_key()
