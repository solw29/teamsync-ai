import base64
import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import select

from .errors import DomainError
from .models import Installation, Session, User, now


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password):
    salt = secrets.token_bytes(16)
    value = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return base64.b64encode(salt + value).decode()


def password_matches(password, stored):
    try:
        raw = base64.b64decode(stored)
        return secrets.compare_digest(
            hashlib.scrypt(password.encode(), salt=raw[:16], n=16384, r=8, p=1),
            raw[16:],
        )
    except (ValueError, TypeError):
        return False


def bootstrap(db, settings, token, username, password):
    if not settings.bootstrap_token or not secrets.compare_digest(
        token, settings.bootstrap_token
    ):
        raise DomainError("invalid_bootstrap", 403)
    if db.get(Installation, 1):
        raise DomainError("already_initialized", 409)
    db.add(Installation(id=1))
    db.add(User(username=username, password_hash=password_hash(password)))
    db.flush()  # Installation primary key arbitrates concurrent initialization.


def login(db, username, password, seconds):
    user = db.scalar(select(User).where(User.username == username))
    if not user or not password_matches(password, user.password_hash):
        raise DomainError("invalid_credentials", 401)
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.add(
        Session(
            token_hash=digest(token),
            csrf_hash=digest(csrf),
            user_id=user.id,
            expires_at=now() + timedelta(seconds=seconds),
        )
    )
    return token, csrf, user


def authenticate(db, token):
    session = db.get(Session, digest(token)) if token else None
    if not session or session.expires_at.replace(tzinfo=now().tzinfo) <= now():
        raise DomainError("authentication_required", 401)
    return session, db.get(User, session.user_id)
