"""Chronos 1.0 — consumidor local e scheduler opcional da Fase 7."""
import argparse
from pathlib import Path
import sys
from time import sleep
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import Settings
from app.core.database import build_engine, session_factory
from app.services.automation_worker import work_once

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--scheduler", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=2)
    args = parser.parse_args()
    if not 0.2 <= args.poll_seconds <= 60:
        parser.error("Intervalo deve ficar entre 0.2 e 60 segundos")
    settings = Settings(); engine = build_engine(settings)
    if engine is None:
        parser.error("Configure o banco e execute as migrations")
    factory = session_factory(engine)
    try:
        while True:
            processed = work_once(factory, settings, args.scheduler)
            if args.once:
                print("Chronos 1.0: evento processado." if processed else "Chronos 1.0: fila vazia.")
                break
            if not processed:
                sleep(args.poll_seconds)
    except KeyboardInterrupt:
        pass
    finally:
        engine.dispose()
