import hashlib
import hmac
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import case, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.api.dependencies import aware, fail
from app.core.security import access_token, dummy_hash, new_refresh_token, token_hash, verify_password
from app.models.entities import LoginThrottle, Organization, RefreshSession, User, now
from app.services.audit import audit


def throttle(session, settings, identity, ip):
    instant = now()
    cutoff = instant - timedelta(seconds=settings.login_window_seconds)
    insert = pg_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
    for scope, value, limit in [("ip", ip, settings.login_limit * 5), ("account", identity, settings.login_limit)]:
        digest = hmac.new(settings.jwt_secret.get_secret_value().encode(), f"{scope}:{value}".encode(), hashlib.sha256).hexdigest()
        expired = LoginThrottle.window_start <= cutoff
        statement = insert(LoginThrottle).values(id=str(uuid4()), bucket_hash=digest, attempts=1, window_start=instant, created_at=instant)
        statement = statement.on_conflict_do_update(index_elements=[LoginThrottle.bucket_hash], set_={
            "attempts": case((expired, 1), else_=LoginThrottle.attempts + 1),
            "window_start": case((expired, instant), else_=LoginThrottle.window_start),
        }).returning(LoginThrottle.attempts)
        attempts = session.scalar(statement)
        if attempts > limit:
            session.commit()
            fail(429, "LOGIN_RATE_LIMIT", "Muitas tentativas. Aguarde a janela de autenticação.")
    session.commit()  # Persistir inclusive tentativas com credenciais inválidas.


def issue_session(session, user, settings, family=None):
    family = family or str(uuid4())
    raw = new_refresh_token()
    session.add(RefreshSession(organization_id=user.organization_id, user_id=user.id,
        family_id=family, token_hash=token_hash(raw), expires_at=now() + timedelta(days=settings.refresh_days)))
    return {"access_token": access_token(user, family, settings), "refresh_token": raw,
            "token_type": "bearer", "expires_in": settings.access_minutes * 60}


def login(session, settings, payload, ip, correlation):
    username = payload.username.lower()
    throttle(session, settings, f"{payload.organization}:{username}", ip)
    org = session.scalar(select(Organization).where(Organization.slug == payload.organization))
    user = session.scalar(select(User).where(User.organization_id == org.id, User.username == username)) if org else None
    valid = verify_password(payload.password.get_secret_value(), user.password_hash if user else dummy_hash)
    if not user or not valid or not user.active:
        fail(401, "INVALID_CREDENTIALS", "Credenciais inválidas.")
    tokens = issue_session(session, user, settings)
    audit(session, user.organization_id, user.id, "auth.login", "users", user.id, correlation)
    session.commit()
    return tokens


def revoke_family(session, record):
    session.execute(update(RefreshSession).where(RefreshSession.organization_id == record.organization_id,
        RefreshSession.user_id == record.user_id, RefreshSession.family_id == record.family_id).values(revoked_at=now()))


def refresh(session, settings, raw, correlation):
    record = session.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash(raw)).with_for_update())
    if not record:
        fail(401, "INVALID_REFRESH", "Sessão inválida ou expirada.")
    if record.consumed_at or record.revoked_at:
        revoke_family(session, record)
        audit(session, record.organization_id, record.user_id, "auth.refresh_reuse", "users", record.user_id, correlation)
        session.commit()
        fail(401, "REFRESH_REUSED", "Sessão revogada. Faça login novamente.")
    if aware(record.expires_at) <= now():
        fail(401, "INVALID_REFRESH", "Sessão inválida ou expirada.")
    user = session.get(User, record.user_id)
    if not user or not user.active or user.organization_id != record.organization_id:
        fail(401, "INVALID_REFRESH", "Sessão inválida ou expirada.")
    consumed = session.execute(update(RefreshSession).where(RefreshSession.id == record.id,
        RefreshSession.consumed_at.is_(None), RefreshSession.revoked_at.is_(None)).values(consumed_at=now()))
    if consumed.rowcount != 1:
        session.rollback()
        fail(401, "INVALID_REFRESH", "Sessão já utilizada.")
    tokens = issue_session(session, user, settings, record.family_id)
    audit(session, user.organization_id, user.id, "auth.refresh", "users", user.id, correlation)
    session.commit()
    return tokens
