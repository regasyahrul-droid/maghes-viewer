"""Akun MAGHES publik dari Streamlit secrets; tanpa password di repository."""
import hashlib
import hmac
import streamlit as st


def load_accounts():
    try:
        source = st.secrets["accounts"]
        return {str(name): dict(values) for name, values in source.items()}
    except (KeyError, FileNotFoundError, TypeError):
        return {}


def authenticate(accounts, username, password):
    account = accounts.get(username)
    encoded = account.get("password_hash", "") if isinstance(account, dict) else ""
    try:
        method, n, r, p, salt, digest = encoded.split("$")
        if method != "scrypt":
            return None
        n, r, p = int(n), int(r), int(p)
        if (n, r, p) != (16384, 8, 5):
            return None
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=n, r=r, p=p,
            dklen=len(bytes.fromhex(digest))
        )
        if hmac.compare_digest(actual, bytes.fromhex(digest)):
            return account
    except (ValueError, TypeError, MemoryError):
        pass
    return None
