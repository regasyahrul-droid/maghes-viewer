"""Akun MAGHES publik dari Streamlit secrets; tanpa password di repository."""
import base64
import binascii
import hashlib
import hmac

import streamlit as st


def load_accounts():
    try:
        source = st.secrets["accounts"]
        return {str(name): dict(values) for name, values in source.items()}
    except (KeyError, FileNotFoundError, TypeError):
        return {}


def _decode_hash_part(value, expected_length):
    """Baca format Base64 MAGHES intranet dan format hex lama viewer."""
    try:
        decoded = base64.b64decode(value, validate=True)
        if len(decoded) == expected_length:
            return decoded
    except (binascii.Error, ValueError, TypeError):
        pass
    decoded = bytes.fromhex(value)
    if len(decoded) != expected_length:
        raise ValueError("Panjang komponen hash tidak valid.")
    return decoded


def authenticate(accounts, username, password):
    account = accounts.get(username)
    encoded = account.get("password_hash", "") if isinstance(account, dict) else ""
    try:
        method, n, r, p, salt_text, digest_text = encoded.split("$")
        if method != "scrypt":
            return None
        n, r, p = int(n), int(r), int(p)
        if (n, r, p) not in ((16384, 8, 1), (16384, 8, 5)):
            return None
        salt = _decode_hash_part(salt_text, 16)
        expected = _decode_hash_part(digest_text, 32)
        actual = hashlib.scrypt(
            password.encode(), salt=salt, n=n, r=r, p=p, dklen=len(expected)
        )
        if hmac.compare_digest(actual, expected):
            return account
    except (ValueError, TypeError, MemoryError):
        pass
    return None
