"""Chronos 1.0 — corrigir somente horários legados confirmados da fixture."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import Settings
from app.core.database import build_engine, session_factory
from app.models.entities import Organization
from app.services.demo import load_demo
from app.services.demo_time_repair import repair_demo_times
from app.services.seed import demo_id

settings = Settings()
engine = build_engine(settings)
if engine is None:
    raise RuntimeError("Configure o banco local primeiro")
try:
    with session_factory(engine).begin() as session:
        org = session.get(Organization, demo_id("organization"))
        if org is None:
            raise RuntimeError("Demonstração esperada não encontrada")
        print({"product": "Chronos 1.0", **repair_demo_times(session, org, load_demo(), settings.environment)})
finally:
    engine.dispose()
