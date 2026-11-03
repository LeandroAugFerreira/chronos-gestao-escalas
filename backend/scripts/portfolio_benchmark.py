"""Chronos 1.0: microbenchmark fictício, sem medir trabalho humano ou ganhos de mercado."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform
from statistics import median
import sys
from time import perf_counter
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import PROJECT_ROOT
from app.services.optimizer import check_solution, prepare, solve


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def first_fit(data):
    selected, trials = [], 0
    by_id = {c["id"]: c for c in data["candidates"]}
    for cell in sorted(data["cells"], key=lambda c: (c["start"], c["activity"])):
        active = set(cell["candidates"]) & set(selected)
        people = {by_id[i]["employee_id"] for i in active}
        while len(people) < cell["required"]:
            accepted = False
            for ident in sorted(cell["candidates"], key=lambda i: (by_id[i]["employee_id"], i)):
                if ident in selected or by_id[ident]["employee_id"] in people:
                    continue
                trials += 1
                if check_solution(data, selected + [ident])["valid"]:
                    selected.append(ident); people.add(by_id[ident]["employee_id"]); accepted = True
                    break
            if not accepted:
                break
    return selected, trials


def run_benchmark(snapshot, repetitions=3):
    if not 1 <= repetitions <= 10:
        raise ValueError("Use entre 1 e 10 repetições")
    original = canonical(snapshot)
    cases = []
    for count in [3, 2]:
        case = deepcopy(snapshot)
        case["options"]["mode"] = "diagnostic"
        case["facts"]["employees"] = case["facts"]["employees"][:count]
        ids = {p["id"] for p in case["facts"]["employees"]}
        case["facts"]["contracts"] = [c for c in case["facts"]["contracts"] if c["employee_id"] in ids]
        digest = hashlib.sha256(canonical(case)).hexdigest()
        manual_times, solver_times = [], []
        for _ in range(repetitions):
            started = perf_counter(); data = prepare(deepcopy(case)); selected, trials = first_fit(data)
            manual = check_solution(data, selected); manual_times.append(perf_counter() - started)
            started = perf_counter(); result = solve(deepcopy(case)); solver_times.append(perf_counter() - started)
            assert result["verification"]["valid"] and manual["valid"]
        required = manual["required_staff_minutes"]
        def metrics(verification, assignments, cost):
            return {"required_staff_minutes": verification["required_staff_minutes"], "covered_staff_minutes": verification["covered_staff_minutes"],
                "uncovered_staff_minutes": verification["uncovered_staff_minutes"], "coverage_ratio": verification["covered_staff_minutes"] / required if required else None,
                "constraint_error_categories": len(verification["errors"]), "assignments": assignments, "hypothetical_cost_cents": cost,
                "complete_numerical_schedule": bool(verification["valid"] and verification["uncovered_staff_minutes"] == 0)}
        cases.append({"population":count,"input_sha256":digest,"algorithm_version":result["algorithm_version"],"ortools_version":result["ortools_version"],
            "seed":case["options"]["seed"],"workers":case["options"]["workers"],"repetitions":repetitions,
            "manual_simulated_policy": {**metrics(manual,len(selected),sum(c["cost_cents"] for c in data["candidates"] if c["id"] in selected)),
                "policy":"first-fit cronológico, profissional por ID; rejeita restrições pelo mesmo verificador", "candidate_trials_last_run":trials,
                "algorithm_seconds_median":round(median(manual_times),6),"algorithm_seconds_min":round(min(manual_times),6),"algorithm_seconds_max":round(max(manual_times),6)},
            "chronos_solver": {**metrics(result["verification"],len(result["assignments"]),result["estimated_cost_cents"]),"status":result["solver_status"],
                "pipeline_seconds_median":round(median(solver_times),6),"pipeline_seconds_min":round(min(solver_times),6),"pipeline_seconds_max":round(max(solver_times),6),
                "solver_wall_seconds_last_run":round(sum(s["wall_seconds"] for s in result["stages"]),6)}})
    assert canonical(snapshot) == original
    return {"product":"Chronos 1.0","schema":"portfolio-microbenchmark-1.0","simulated":True,
        "fixture_sha256":hashlib.sha256(original).hexdigest(),"python":platform.python_version(),"os":platform.system(),"architecture":platform.machine(),
        "scope":"Microensaio de uma atividade durante um dia, com 3 e 2 profissionais fictícios. Não é benchmark dos 350 colaboradores.",
        "methodology":"Mesmos insumos e verificador; first-fit representa uma política manual simulada implementada em código. Repetições sequenciais, sem medir cliques ou tempo de pessoas.",
        "human_productivity_gain":None,"human_work_time_seconds":None,"observed_financial_savings_cents":None,
        "limits":["Tempos são de execução de algoritmos nesta máquina, não produtividade humana.","Custos imputados por plantão são fictícios e não são salários, pisos ou gastos observados.",
            "Cobertura numérica e status de teste não certificam validade jurídica ou dimensionamento hospitalar.","Comparar custo de cobertura incompleta com completa não demonstra economia.",
            "O caso é pequeno e favorável às duas políticas; não permite extrapolação de desempenho ou ganhos para o hospital."],"cases":cases}


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture",type=Path,default=PROJECT_ROOT/"data/synthetic/portfolio_benchmark.json")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--repetitions",type=int,default=3)
    args=parser.parse_args()
    report=run_benchmark(json.loads(args.fixture.read_text(encoding="utf-8")),args.repetitions)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"product":"Chronos 1.0","cases":len(report["cases"]),"simulated":True,"output":str(args.output)},ensure_ascii=False))
