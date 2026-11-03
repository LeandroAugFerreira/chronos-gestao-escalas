"""Chronos 1.0: sessão web com refresh HttpOnly e CSRF assinado ligado à família."""

import hashlib
import hmac
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select

from app.api.auth import me
from app.api.dependencies import fail, get_db, get_principal, security_ready
from app.core.security import token_hash
from app.models.entities import RefreshSession
from app.schemas.phase2 import LoginInput, MeResponse
from app.services import auth
from app.services.audit import audit
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/session", tags=["Sessão do navegador"])


class BrowserSessionResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    csrf_token: str
    user: MeResponse


def cookie_names(settings):
    prefix = "__Host-" if settings.cookie_secure else ""
    return prefix + "chronos-refresh", prefix + "chronos-csrf"


def csrf_signature(nonce, family, settings):
    return hmac.new(settings.jwt_secret.get_secret_value().encode(),
                    f"chronos-csrf:{family}:{nonce}".encode(), hashlib.sha256).hexdigest()


def csrf_valid(token, family, settings):
    try:
        nonce, signature = token.rsplit(".", 1)
        issued = int(nonce.split(":", 1)[0])
        return 0 <= int(time.time()) - issued <= 3600 and hmac.compare_digest(signature, csrf_signature(nonce, family, settings))
    except (ValueError, AttributeError):
        return False


def new_csrf(family, settings):
    nonce = f"{int(time.time())}:{secrets.token_urlsafe(24)}"
    return nonce + "." + csrf_signature(nonce, family, settings)


def current_record(request, session):
    raw = request.cookies.get(cookie_names(request.app.state.settings)[0])
    return session.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash(raw))) if raw else None


def origin_guard(request):
    origin = request.headers.get("origin")
    allowed = {s.strip().rstrip("/") for s in request.app.state.settings.allowed_origins.split(",")}
    if origin not in allowed or request.headers.get("sec-fetch-site") == "cross-site":
        fail(403, "ORIGIN_REJECTED", "Origem da sessão não autorizada.")


def verify_csrf(request: Request, session=Depends(get_db)):
    security_ready(request)
    origin_guard(request)
    settings = request.app.state.settings
    cookie = request.cookies.get(cookie_names(settings)[1], "")
    header = request.headers.get("x-csrf-token", "")
    record = current_record(request, session)
    family = record.family_id if record else "anonymous"
    if not cookie or not hmac.compare_digest(cookie, header) or not csrf_valid(cookie, family, settings):
        fail(403, "CSRF_REJECTED", "Sessão de formulário expirada. Atualize e tente novamente.")
    return record


def set_cookie(response, name, value, settings, max_age):
    response.set_cookie(name, value, max_age=max_age, path="/", secure=settings.cookie_secure,
                        httponly=True, samesite="strict")


def clear_cookies(response, settings):
    for name in cookie_names(settings):
        response.delete_cookie(name, path="/", secure=settings.cookie_secure, httponly=True, samesite="strict")


def session_response(tokens, request, response, session):
    settings = request.app.state.settings
    principal = get_principal(request, HTTPAuthorizationCredentials(scheme="Bearer", credentials=tokens["access_token"]), session)
    record = session.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash(tokens["refresh_token"])))
    csrf = new_csrf(record.family_id, settings)
    refresh_name, csrf_name = cookie_names(settings)
    set_cookie(response, refresh_name, tokens["refresh_token"], settings, settings.refresh_days * 86400)
    set_cookie(response, csrf_name, csrf, settings, 3600)
    return {key: tokens[key] for key in ["access_token", "token_type", "expires_in"]} | {"csrf_token": csrf, "user": me(principal)}


@router.get("/csrf")
def get_csrf(request: Request, response: Response, session=Depends(get_db)):
    security_ready(request)
    if request.headers.get("origin"):
        origin_guard(request)
    record = current_record(request, session)
    family = record.family_id if record else "anonymous"
    settings = request.app.state.settings
    name = cookie_names(settings)[1]
    token = request.cookies.get(name)
    if not csrf_valid(token, family, settings):
        token = new_csrf(family, settings)
    set_cookie(response, name, token, settings, 3600)
    return {"csrf_token": token}


@router.post("/login", response_model=BrowserSessionResponse)
def login(payload: LoginInput, request: Request, response: Response, record=Depends(verify_csrf), session=Depends(get_db)):
    tokens = auth.login(session, request.app.state.settings, payload,
                        request.client.host if request.client else "local", request.state.correlation_id)
    if record:
        auth.revoke_family(session, record)
        session.commit()
    return session_response(tokens, request, response, session)


@router.post("/refresh", response_model=BrowserSessionResponse)
def refresh(request: Request, response: Response, record=Depends(verify_csrf), session=Depends(get_db)):
    settings = request.app.state.settings
    raw = request.cookies.get(cookie_names(settings)[0], "")
    try:
        tokens = auth.refresh(session, settings, raw, request.state.correlation_id)
    except HTTPException as exc:
        error = JSONResponse(status_code=exc.status_code,
            content={**exc.detail, "correlation_id": request.state.correlation_id}, headers={"WWW-Authenticate": "Bearer"})
        clear_cookies(error, settings)
        return error
    return session_response(tokens, request, response, session)


@router.post("/logout", status_code=204)
def logout(request: Request, record=Depends(verify_csrf), session=Depends(get_db)):
    if record:
        auth.revoke_family(session, record)
        audit(session, record.organization_id, record.user_id, "auth.logout", "users", record.user_id, request.state.correlation_id)
        session.commit()
    response = Response(status_code=204)
    clear_cookies(response, request.app.state.settings)
    return response
