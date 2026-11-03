"""File-based worker protocol for a windowed executable without standard streams."""
import json
from pathlib import Path


def solve_files(source, target):
    from app.services.optimizer import ModelLimit, solve
    source, target = Path(source).resolve(), Path(target).resolve()
    if source.parent != target.parent or source == target or target.exists() or source.stat().st_size > 16000000:
        raise ValueError("Invalid isolated solver input/output")
    try:
        result = {"result": solve(json.loads(source.read_text(encoding="utf-8")))}
    except ModelLimit as error:
        result = {"error_code": str(error)}
    except Exception:
        result = {"error_code": "SOLVER_FAILED"}
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream)
