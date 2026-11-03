from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from sqlalchemy.exc import IntegrityError, OperationalError

from app.api.routes import router as checkpoint_router
from app.api.auth import router as auth_router
from app.api.resources import router as resource_router
from app.api.browser_session import router as session_router
from app.api.scheduling import router as scheduling_router
from app.api.simulation import router as simulation_router
from app.api.optimization import router as optimization_router
from app.api.automation import router as automation_router
from app.api.analytics import router as analytics_router
from app.core.config import PRODUCT_TITLE, PRODUCT_VERSION, Settings
from app.core.database import build_engine, session_factory
from app.core.request_limits import RequestLimits, SECURITY_HEADERS

def create_app(settings: Settings | None = None):
    settings = settings or Settings()
    production = settings.environment == "production"
    application = FastAPI(title=PRODUCT_TITLE, version=PRODUCT_VERSION,
        docs_url=None if production else "/docs", redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
        description="Fase 9: segurança, recuperação e validação integrada dos módulos Chronos 1.0.")
    engine = build_engine(settings)
    application.state.settings = settings
    application.state.engine = engine
    application.state.session_factory = session_factory(engine) if engine else None
    application.add_middleware(RequestLimits, max_bytes=settings.max_request_bytes, body_seconds=settings.request_body_seconds)
    application.add_middleware(CORSMiddleware, allow_origins=[s.strip() for s in settings.allowed_origins.split(",") if s.strip()],
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"], allow_headers=["Accept", "Authorization", "Content-Type", "Idempotency-Key"], expose_headers=["X-Correlation-ID", "Idempotency-Replayed"], allow_credentials=False)


    @application.middleware("http")
    async def correlation(request, call_next):
        request.state.correlation_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        if getattr(request.state, "idempotent_replay", False):
            response.headers["Idempotency-Replayed"] = "true"
        if request.url.path.startswith("/api/v1/"):
            response.headers["Cache-Control"] = "no-store"
        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value
        return response

    def error(request, status, content):
        headers = {**SECURITY_HEADERS, "X-Correlation-ID": request.state.correlation_id, "Cache-Control": "no-store"}
        if status == 401:
            headers["WWW-Authenticate"] = "Bearer"
        return JSONResponse(status_code=status, content={**content, "correlation_id": request.state.correlation_id}, headers=headers)

    @application.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "HTTP_ERROR", "message": str(exc.detail)}
        return error(request, exc.status_code, detail)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return error(request, 422, {"code": "VALIDATION_ERROR", "message": "Verifique os campos informados.",
            "field_errors": [{"location": [str(part) for part in item["loc"]], "type": item["type"]} for item in exc.errors()]})

    @application.exception_handler(IntegrityError)
    async def integrity_error(request: Request, _: IntegrityError):
        return error(request, 409, {"code": "INTEGRITY_CONFLICT", "message": "Dados duplicados ou referências incompatíveis. Nenhuma alteração foi confirmada."})

    @application.exception_handler(OperationalError)
    async def database_error(request: Request, _: OperationalError):
        return error(request, 503, {"code": "DATABASE_UNAVAILABLE", "message": "Banco indisponível. Verifique configuração e migrations."})

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        import logging
        logging.getLogger("chronos.errors").error("Unhandled error %s (%s)", request.state.correlation_id, type(exc).__name__)
        return error(request, 500, {"code": "INTERNAL_ERROR", "message": "Falha interna. Informe o identificador da requisição ao suporte."})

    application.include_router(checkpoint_router)
    application.include_router(auth_router)
    application.include_router(resource_router)
    application.include_router(session_router)
    application.include_router(scheduling_router)
    application.include_router(simulation_router)
    application.include_router(optimization_router)
    application.include_router(automation_router)
    application.include_router(analytics_router)
    return application


app = create_app()
