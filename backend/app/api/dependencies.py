from dataclasses import dataclass
from datetime import UTC

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.core.security import decode_access
from app.models.entities import Permission, RefreshSession, RolePermission, User, UserRole, now

bearer = HTTPBearer(auto_error=False)


def fail(status, code, message):
    raise HTTPException(status_code=status, detail={"code": code, "message": message})


def aware(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def get_db(request: Request):
    factory = request.app.state.session_factory
    if factory is None:
        fail(503, "DATABASE_NOT_CONFIGURED", "Configure o banco e execute as migrations.")
    with factory() as session:
        try:
            yield session
        finally:
            session.rollback()


def security_ready(request):
    if not request.app.state.settings.jwt_secret.get_secret_value():
        fail(503, "AUTH_NOT_CONFIGURED", "Configure um segredo JWT seguro antes de autenticar.")


@dataclass
class Principal:
    user: User
    # Cada permissão resolve seu próprio escopo; uma permissão ampla não amplia outra.
    scopes: dict[str, set[str] | None]

    def permits(self, permission, unit=None):
        if permission not in self.scopes:
            return False
        allowed = self.scopes[permission]
        return allowed is None or unit is not None and unit in allowed


def get_principal(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer), session=Depends(get_db)):
    security_ready(request)
    if credentials is None:
        fail(401, "UNAUTHORIZED", "Autenticação necessária.")
    try:
        claims = decode_access(credentials.credentials, request.app.state.settings)
    except jwt.PyJWTError:
        fail(401, "INVALID_TOKEN", "Sessão inválida ou expirada.")
    user = session.scalar(select(User).where(User.id == claims["sub"], User.organization_id == claims["org"], User.active.is_(True)))
    if not user:
        fail(401, "INVALID_TOKEN", "Sessão inválida ou expirada.")
    if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
        from app.services.organization_lock import lock_organization
        lock_organization(session, user.organization_id)
    live = session.scalar(select(RefreshSession.id).where(RefreshSession.organization_id == user.organization_id,
        RefreshSession.user_id == user.id, RefreshSession.family_id == claims["sid"],
        RefreshSession.revoked_at.is_(None), RefreshSession.consumed_at.is_(None), RefreshSession.expires_at > now()))
    if not live:
        fail(401, "INVALID_TOKEN", "Sessão inválida ou expirada.")
    return principal_for_user(session, user)


def principal_for_user(session, user):
    grants = session.execute(select(Permission.code, UserRole.unit_id).join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id).where(UserRole.organization_id == user.organization_id, UserRole.user_id == user.id))
    scopes = {}
    for permission, unit in grants:
        if permission not in scopes:
            scopes[permission] = set()
        if unit is None:
            scopes[permission] = None
        elif scopes[permission] is not None:
            scopes[permission].add(unit)
    return Principal(user, scopes)


def require(permission):
    def dependency(principal=Depends(get_principal)):
        if permission not in principal.scopes:
            fail(403, "FORBIDDEN", "Permissão insuficiente.")
        return principal
    return dependency
