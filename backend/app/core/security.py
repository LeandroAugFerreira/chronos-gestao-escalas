import hashlib
import secrets
from datetime import timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.models.entities import now

# Argon2id: memória 19 MiB, duas iterações e uma lane; calibrar em produção.
hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
dummy_hash = hasher.hash("dummy-password-never-used-for-login")
ROLE_PERMISSIONS = {
    "admin": {"org:read", "org:write", "people:read", "people:write", "finance:read", "catalog:read", "catalog:write", "users:write", "audit:read"},
    "hr": {"org:read", "people:read", "people:write", "finance:read", "catalog:read", "catalog:write"},
    "manager": {"org:read", "people:read", "catalog:read"},
    "finance": {"org:read", "finance:read", "catalog:read"},
    "analyst": {"org:read", "catalog:read"},
    "demo": {"org:read", "catalog:read"},
}
for _role in ["admin", "hr", "manager"]:
    ROLE_PERMISSIONS[_role].update({"schedule:read", "schedule:write", "rules:read"})
for _role in ["admin", "hr"]:
    ROLE_PERMISSIONS[_role].add("rules:write")
ROLE_PERMISSIONS["analyst"].add("rules:read")
for _role in ["admin", "hr", "manager", "analyst", "finance"]:
    ROLE_PERMISSIONS[_role].add("scenario:read")
for _role in ["admin", "hr", "manager", "analyst"]:
    ROLE_PERMISSIONS[_role].add("scenario:write")
for _role in ["admin", "hr", "finance"]:
    ROLE_PERMISSIONS[_role].add("finance:simulate")
for _role in ["admin", "hr", "manager", "analyst"]:
    ROLE_PERMISSIONS[_role].add("optimization:read")
for _role in ["admin", "hr", "manager"]:
    ROLE_PERMISSIONS[_role].update({"optimization:write", "schedule:approve"})
for _role in ["admin", "hr", "manager", "analyst", "finance"]:
    ROLE_PERMISSIONS[_role].add("automation:read")
for _role in ["admin", "hr", "manager"]:
    ROLE_PERMISSIONS[_role].update({"automation:manage", "automation:run"})
for _role in ["admin", "hr"]:
    ROLE_PERMISSIONS[_role].add("integration:manage")


def hash_password(password):
    return hasher.hash(password)


def verify_password(password, encoded):
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def token_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def new_refresh_token():
    return secrets.token_urlsafe(48)


def access_token(user, family_id, settings):
    issued = now()
    payload = {"sub": user.id, "org": user.organization_id, "sid": family_id,
               "jti": secrets.token_hex(16), "type": "access", "iss": "chronos", "aud": "chronos-api",
               "iat": issued, "nbf": issued, "exp": issued + timedelta(minutes=settings.access_minutes)}
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm="HS256")


def decode_access(token, settings):
    claims = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=["HS256"],
                        audience="chronos-api", issuer="chronos",
                        options={"require": ["sub", "org", "sid", "jti", "iat", "nbf", "exp", "type"]})
    if claims["type"] != "access":
        raise jwt.InvalidTokenError("Tipo inválido")
    return claims
