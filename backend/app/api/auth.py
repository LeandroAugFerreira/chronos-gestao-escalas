from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select

from app.api.dependencies import get_db, get_principal, security_ready
from app.core.security import token_hash
from app.models.entities import RefreshSession
from app.schemas.phase2 import LoginInput, MeResponse, RefreshInput, TokenResponse
from app.services import auth
from app.services.audit import audit

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginInput, request: Request, response: Response, session=Depends(get_db)):
    security_ready(request)
    response.headers["Cache-Control"] = "no-store"
    return auth.login(session, request.app.state.settings, payload, request.client.host if request.client else "local", request.state.correlation_id)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshInput, request: Request, response: Response, session=Depends(get_db)):
    security_ready(request)
    response.headers["Cache-Control"] = "no-store"
    return auth.refresh(session, request.app.state.settings, payload.refresh_token.get_secret_value(), request.state.correlation_id)


@router.post("/logout", status_code=204)
def logout(payload: RefreshInput, request: Request, session=Depends(get_db)):
    record = session.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash(payload.refresh_token.get_secret_value())).with_for_update())
    if record:
        auth.revoke_family(session, record)
        audit(session, record.organization_id, record.user_id, "auth.logout", "users", record.user_id, request.state.correlation_id)
        session.commit()
    return Response(status_code=204)


@router.get("/me", response_model=MeResponse)
def me(principal=Depends(get_principal)):
    return {"id": principal.user.id, "username": principal.user.username,
            "organization_id": principal.user.organization_id,
            "permissions": {key: None if units is None else sorted(units) for key, units in principal.scopes.items()}}
