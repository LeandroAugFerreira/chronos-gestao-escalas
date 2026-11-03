from fastapi import APIRouter, HTTPException
from fastapi import Depends
from sqlalchemy import text

from app.api.dependencies import fail, get_db

from app.core.config import PRODUCT_VERSION
from app.schemas.demo import DemoSummary, ErrorResponse
from app.services.demo import load_demo, summarize_demo

router = APIRouter(prefix="/api/v1")


@router.get("/health", tags=["Checkpoint"])
def health() -> dict:
    return {"status": "ok", "product": "Chronos", "version": PRODUCT_VERSION, "phase": 9}


@router.get("/health/ready", tags=["Checkpoint"])
def ready(session=Depends(get_db)):
    revision = session.scalar(text("SELECT version_num FROM alembic_version"))
    if revision != "010_pattern_revision":
        fail(503, "SCHEMA_OUTDATED", "Execute as migrations antes de utilizar os cadastros.")
    return {"status": "ready", "product": "Chronos", "version": PRODUCT_VERSION,
            "phase": 9, "database": session.bind.dialect.name, "schema": revision}


@router.get("/demo/summary", response_model=DemoSummary, tags=["Demonstração sintética"],
            responses={503: {"model": ErrorResponse}})
def demo_summary() -> DemoSummary:
    try:
        return summarize_demo(load_demo())
    except (OSError, ValueError, KeyError, TypeError):
        # Não expor caminhos locais, payloads inválidos ou detalhes internos ao cliente.
        raise HTTPException(status_code=503, detail={
            "code": "DEMO_UNAVAILABLE", "message": "Base de demonstração indisponível. Gere os dados sintéticos.",
        }) from None
