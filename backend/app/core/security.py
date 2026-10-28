import base64
import hashlib
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from cryptography.fernet import Fernet

from app.core.config import get_settings


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt(get_settings().BCRYPT_ROUNDS)).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode()[:72], hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: str, org_id: str, role: str) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "org": org_id, "role": role, "exp": exp, "typ": "access"}, s.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    data = jwt.decode(token, get_settings().SECRET_KEY, algorithms=["HS256"])
    if data.get("typ") != "access":
        raise jwt.InvalidTokenError("wrong token type")
    return data


def sign_state(payload: dict, minutes: int = 10) -> str:
    s = get_settings()
    return jwt.encode({**payload, "typ": "oauth_state", "exp": datetime.now(timezone.utc) + timedelta(minutes=minutes)}, s.SECRET_KEY, algorithm="HS256")


def verify_state(state: str) -> dict:
    data = jwt.decode(state, get_settings().SECRET_KEY, algorithms=["HS256"])
    if data.get("typ") != "oauth_state":
        raise jwt.InvalidTokenError("wrong token type")
    return data


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(get_settings().SECRET_KEY.encode()).digest())
    return Fernet(key)


def encrypt_secret(value: str | None) -> str | None:
    return _fernet().encrypt(value.encode()).decode() if value else None


def decrypt_secret(value: str | None) -> str | None:
    return _fernet().decrypt(value.encode()).decode() if value else None


class RateLimiter:
    """Tiny in-memory sliding-window limiter (single process)."""

    def __init__(self):
        self.hits: dict[str, deque] = defaultdict(deque)

    def reset(self):
        self.hits.clear()

    def allow(self, key: str, limit: int, window: int) -> bool:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


login_limiter = RateLimiter()
