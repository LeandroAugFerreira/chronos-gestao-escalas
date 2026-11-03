"""Solver subprocess: receives business facts only; never opens the database."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.optimizer import ModelLimit, solve

if __name__ == "__main__":
    try:
        snapshot = json.load(sys.stdin)
        print(json.dumps({"result": solve(snapshot)}))
    except ModelLimit as exc:
        print(json.dumps({"error_code": str(exc)}))
    except Exception:
        # No traceback or environment information crosses the process boundary.
        print(json.dumps({"error_code": "SOLVER_FAILED"}))
