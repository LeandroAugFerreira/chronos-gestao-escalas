"""Publish only fictional, precomputed examples from the real 2.0 comparator."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.schemas.labor_transition import TransitionInput
from app.services.labor_transition import compare, metadata


def build():
    presets = [
        ("base", "Base histórica · 44 horas", dict(reference_date="2026-12-15", planned_weekly_minutes=2640, rest_days_24h=1)),
        ("transition", "Transição · 42 horas", dict(reference_date="2026-12-16", planned_weekly_minutes=2520, planned_daily_minutes=504, collective_status="absent_at_cutoff", use_interim_daily_exception=True)),
        ("final", "Etapa seguinte · 40 horas", dict(reference_date="2027-12-16", planned_weekly_minutes=2400)),
    ]
    return {**metadata(), "synthetic": True, "delivery": "Precomputed examples; no API or OR-Tools runs in the static portfolio.",
            "examples": [{"id": key, "label": label, "result": compare(TransitionInput(**values))} for key, label, values in presets]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[2] / "data/synthetic/labor_transition_demo.json")
    args = parser.parse_args()
    if args.check:
        assert json.loads(args.output.read_text(encoding="utf-8")) == build(), "Regenerate the transition fixture"
    else:
        args.output.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Chronos 2.0: três exemplos fictícios reproduzíveis, calculados pelo comparador real.")
