"""Chronos 1.0 — worker local da Fase 6."""
import argparse
import sys
from pathlib import Path
from time import sleep
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import Settings
from app.core.database import build_engine, session_factory
from app.services.optimization_worker import work_once

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=2)
    args = parser.parse_args()
    if not 0.2 <= args.poll_seconds <= 60:
        parser.error("poll-seconds deve ficar entre 0.2 e 60")
    settings = Settings()
    engine = build_engine(settings)
    if engine is None or not settings.jwt_secret.get_secret_value():
        parser.error("Configure banco e autenticação antes de iniciar o worker")
    factory = session_factory(engine)
    try:
        while True:
            processed = work_once(factory, settings, args.runtime_dir)
            if args.once:
                print("Chronos 1.0: tarefa processada." if processed else "Chronos 1.0: fila vazia.")
                return
            if not processed:
                sleep(args.poll_seconds)
    except KeyboardInterrupt:
        pass
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
