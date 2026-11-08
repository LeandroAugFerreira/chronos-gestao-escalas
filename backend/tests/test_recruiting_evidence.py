"""Contratos de evidência do microensaio sintético publicado no portfólio.

Não compara com produtividade humana e não representa dimensionamento real.
"""
import hashlib
import json
from pathlib import Path

from scripts.portfolio_benchmark import canonical, run_benchmark

ROOT = Path(__file__).resolve().parents[2]


def files():
    fixture = json.loads((ROOT / "data/synthetic/portfolio_benchmark.json").read_text(encoding="utf-8"))
    published = json.loads((ROOT / "docs/portfolio/benchmark.json").read_text(encoding="utf-8"))
    return fixture, published


def test_public_benchmark_has_same_input_and_no_human_roi():
    fixture, published = files()
    digest = hashlib.sha256(canonical(fixture)).hexdigest()
    assert published["fixture_sha256"] == digest
    assert published["simulated"] is True
    assert published["human_productivity_gain"] is None
    assert published["human_work_time_seconds"] is None
    assert published["observed_financial_savings_cents"] is None
    assert [c["population"] for c in published["cases"]] == [3, 2]


def test_optimizer_and_first_fit_have_validity_and_gap_explicit():
    fixture, _ = files()
    measured = run_benchmark(fixture, repetitions=1)
    assert measured["simulated"] is True
    for case in measured["cases"]:
        manual = case["manual_simulated_policy"]
        solver = case["chronos_solver"]
        assert manual["constraint_error_categories"] == 0
        assert solver["constraint_error_categories"] == 0
        assert manual["required_staff_minutes"] == solver["required_staff_minutes"] == 1440
        assert manual["covered_staff_minutes"] == solver["covered_staff_minutes"]
        assert manual["hypothetical_cost_cents"] == solver["hypothetical_cost_cents"]
        if case["population"] == 3:
            assert solver["covered_staff_minutes"] == 1440
            assert solver["uncovered_staff_minutes"] == 0
            assert solver["complete_numerical_schedule"] is True
        else:
            assert solver["covered_staff_minutes"] == 960
            assert solver["uncovered_staff_minutes"] == 480
            assert solver["complete_numerical_schedule"] is False
        # OPTIMAL em modo diagnóstico não significa cobertura completa.
        assert solver["complete_numerical_schedule"] == (solver["uncovered_staff_minutes"] == 0)
