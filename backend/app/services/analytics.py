"""Bounded, permission-projected extracts from existing versioned calculations.

No source JSON, payroll snapshot, actor, prompt or automation result is copied.
The extract is a report, never a new labor evaluation or solver decision.
"""
from datetime import UTC, datetime, time
import hashlib
import json
from zoneinfo import ZoneInfo
from sqlalchemy import select
from app.api.dependencies import aware, fail
from app.api.simulation import check_permission
from app.models.entities import (AutomationExecution, FinancialRun, OptimizationRun,
    ScenarioVersion, ScheduleVersion, Unit, now)
from app.repositories.scoped import get_scoped
from app.services.capacity import month_after
from app.services.labor_rules import minutes, segments

SCHEMA = "chronos-report-1.0"
MAX_ROWS = 20000
MAX_BYTES = 8 * 1024 * 1024
# Stable columns also preserve the schema for empty facts.
COLUMNS = {
    "units": ["unit_id", "name_at_extraction", "timezone"],
    "scenario": ["scenario_id", "unit_id", "key", "version", "name", "reference_month", "timezone", "digest", "population_count", "raw_available_minutes", "raw_payable_minutes", "effective_budget_minutes", "required_staff_minutes", "aggregate_gap_lower_bound_minutes"],
    "coverage": ["optimization_id", "scenario_id", "unit_id", "start_date", "end_date_exclusive", "state", "solver_status", "input_digest", "valid", "required_staff_minutes", "covered_staff_minutes", "uncovered_staff_minutes", "assignment_count", "real_minutes", "payable_minutes"],
    "proposals": ["proposal_id", "optimization_id", "scenario_id", "unit_id", "series_id", "version", "state", "revision", "digest"],
    "assignments": ["optimization_id", "scenario_id", "unit_id", "candidate_id", "employee_id", "department_id", "start_at", "end_at", "real_minutes", "payable_minutes"],
    "finance": ["financial_id", "scenario_id", "unit_id", "month", "currency", "digest", "base_payroll_cents", "components_cents", "total_cents"],
    "executions": ["execution_id", "unit_id", "code", "attempt", "state", "source", "started_at", "finished_at"],
}
GRAINS = {
    "units": "Uma unidade autorizada; nome e fuso no instante da extração.",
    "scenario": "Uma versão de cenário; capacidade simulada no mês civil da unidade.",
    "coverage": "Uma execução selecionada; horizonte completo, fim exclusivo; cobertura calculada, não atendimento observado.",
    "proposals": "Uma versão de proposta da execução; estado observado na extração.",
    "assignments": "Uma atribuição inteira da execução, inclusive trechos fora do horizonte; pausas descontadas dos minutos reais.",
    "finance": "Uma projeção selecionada por mês; 12 meses, valores em centavos, sem somar alternativas.",
    "executions": "Uma tentativa de automação iniciada no mês civil do cenário; não é contagem de eventos únicos.",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def bounded(rows):
    result = list(rows)
    if len(result) > MAX_ROWS:
        fail(422, "REPORT_LIMIT", "O relatório excede 20.000 registros. Reduza a seleção.")
    return result


def duration(assignment, paid=False):
    start, end = (datetime.fromisoformat(assignment[key]) for key in ["start_at", "end_at"])
    return sum(minutes(a, b) for a, b in segments(start, end, assignment.get("breaks", []), include_paid=paid))


def extract(session, principal, selection):
    scenario = get_scoped(session, ScenarioVersion, selection.scenario_id, principal, "scenario:read", ScenarioVersion.unit_id)
    unit = session.get(Unit, scenario.unit_id)
    timezone = scenario.capacity["timezone"]
    start = datetime.combine(scenario.reference_month, time(), ZoneInfo(timezone)).astimezone(UTC)
    end = datetime.combine(month_after(scenario.reference_month), time(), ZoneInfo(timezone)).astimezone(UTC)
    if selection.include_people:
        check_permission(principal, "people:read", unit.id)
        if not selection.optimization_id:
            fail(422, "MISSING_OPTIMIZATION", "Selecione uma otimização para incluir atribuições.")
    capacity = scenario.capacity
    tables = {"units": [{"unit_id": unit.id, "name_at_extraction": unit.name, "timezone": unit.timezone}], "scenario": [{"scenario_id": scenario.id, "unit_id": unit.id, "key": scenario.key,
        "version": scenario.version, "name": scenario.name, "reference_month": str(scenario.reference_month),
        "timezone": timezone, "digest": scenario.digest,
        **{key: capacity[key] for key in COLUMNS["scenario"][8:] if key != "digest"}}]}
    # digest is column 7; population and minute fields start at 8.
    sources = [{"kind": "scenario", "id": scenario.id, "digest": scenario.digest}]
    if selection.optimization_id:
        check_permission(principal, "optimization:read", unit.id)
        run = get_scoped(session, OptimizationRun, selection.optimization_id, principal, "optimization:read", OptimizationRun.unit_id)
        if run.scenario_id != scenario.id:
            fail(422, "REPORT_REFERENCE", "A otimização deve pertencer à versão de cenário selecionada.")
        result = run.result
        verification = result.get("verification", {})
        assignments = bounded(result.get("assignments", []))
        fields = ["required_staff_minutes", "covered_staff_minutes", "uncovered_staff_minutes"]
        coverage = {"optimization_id": run.id, "scenario_id": scenario.id, "unit_id": unit.id,
            "start_date": run.inputs["start_date"], "end_date_exclusive": run.inputs["end_date"], "state": run.state,
            "solver_status": result.get("solver_status"), "input_digest": run.input_digest,
            "valid": verification.get("valid"), **{key: verification.get(key) for key in fields},
            "assignment_count": len(assignments) if verification else None,
            "real_minutes": sum(duration(a) for a in assignments) if verification else None,
            "payable_minutes": sum(duration(a, True) for a in assignments) if verification else None}
        measured = [coverage[key] for key in fields]
        if all(value is not None for value in measured) and measured[0] != measured[1] + measured[2]:
            fail(409, "REPORT_RECONCILIATION", "Cobertura armazenada não reconcilia. Revise a execução de origem.")
        tables["coverage"] = [coverage]
        sources.append({"kind": "optimization", "id": run.id, "digest": run.input_digest, "revision": run.revision})
        if principal.permits("schedule:read", unit.id):
            proposals = bounded(session.scalars(select(ScheduleVersion).where(ScheduleVersion.organization_id == principal.user.organization_id,
                ScheduleVersion.run_id == run.id).order_by(ScheduleVersion.id).limit(MAX_ROWS + 1)))
            tables["proposals"] = [{"proposal_id": p.id, "optimization_id": run.id, "scenario_id": scenario.id,
                "unit_id": unit.id, "series_id": p.series_id, "version": p.version, "state": p.state,
                "revision": p.revision, "digest": p.digest} for p in proposals]
        if selection.include_people:
            tables["assignments"] = [{"optimization_id": run.id, "scenario_id": scenario.id, "unit_id": unit.id,
                **{key: a[key] for key in ["candidate_id", "employee_id", "department_id", "start_at", "end_at"]},
                "real_minutes": duration(a), "payable_minutes": duration(a, True)} for a in assignments]
    if selection.financial_id:
        check_permission(principal, "finance:read", unit.id)
        financial = get_scoped(session, FinancialRun, selection.financial_id, principal, "finance:read", FinancialRun.unit_id)
        if financial.scenario_id != scenario.id:
            fail(422, "REPORT_REFERENCE", "A projeção deve pertencer à versão de cenário selecionada.")
        tables["finance"] = [{"financial_id": financial.id, "scenario_id": scenario.id, "unit_id": unit.id,
            "month": month["month"] + "-01", "currency": financial.result["currency"], "digest": financial.digest,
            "base_payroll_cents": month["base_payroll_cents"], "components_cents": sum(c["amount_cents"] for c in month["components"]),
            "total_cents": month["total_cents"]} for month in financial.result["months"]]
        if (sum(m["total_cents"] for m in tables["finance"]) != financial.result["annual_total_cents"] or
                any(m["total_cents"] != m["base_payroll_cents"] + m["components_cents"] for m in tables["finance"])):
            fail(409, "REPORT_RECONCILIATION", "Projeção armazenada não reconcilia. Revise a origem.")
        sources.append({"kind": "financial", "id": financial.id, "digest": financial.digest})
    if principal.permits("automation:read", unit.id):
        query = select(AutomationExecution).where(AutomationExecution.organization_id == principal.user.organization_id,
            AutomationExecution.unit_id == unit.id, AutomationExecution.started_at >= start, AutomationExecution.started_at < end)
        if not principal.permits("audit:read", unit.id):
            query = query.where(AutomationExecution.code != "A07")
        executions = bounded(session.scalars(query.order_by(AutomationExecution.started_at, AutomationExecution.id).limit(MAX_ROWS + 1)))
        tables["executions"] = [{"execution_id": e.id, "unit_id": unit.id, "code": e.code, "attempt": e.attempt,
            "state": e.state, "source": e.source, "started_at": aware(e.started_at).isoformat(),
            "finished_at": aware(e.finished_at).isoformat() if e.finished_at else None} for e in executions]
    bounded(row for rows in tables.values() for row in rows)
    manifest = {"product": "Chronos 1.0", "schema": SCHEMA, "extracted_at": now().isoformat(),
        "organization_id": principal.user.organization_id, "unit_id": unit.id, "unit_name_at_extraction": unit.name,
        "timezone": timezone, "period_start_utc": start.isoformat(), "period_end_utc_exclusive": end.isoformat(),
        "selection": selection.model_dump(exclude={"format"}), "sources": sources,
        "columns": {name: COLUMNS[name] for name in tables}, "grains": {name: GRAINS[name] for name in tables},
        "limits": {"max_rows": MAX_ROWS, "max_bytes": MAX_BYTES},
        "methodology": ["Capacidade é simulação agregada; não comprova cobertura nem dimensionamento profissional.",
            "Cobertura mede postos-minuto do verificador no horizonte completo. Minutos de atribuições medem pessoas e podem diferir.",
            "Custos são projeções com premissas congeladas; não são gastos observados ou economia comprovada.",
            "Cada extração contém uma alternativa selecionada. Histórico de versões não é somável.",
            "Estados de propostas e automações refletem a extração. Guarde o arquivo para reproduzir esse estado.",
            "Minutos são inteiros; valores financeiros são centavos BRL. Ausência de resultado é nulo, nunca zero implícito."]}
    payload = {"schema": SCHEMA, "selection": manifest["selection"], "tables": tables}
    if len(canonical({"manifest": manifest, "tables": tables})) > MAX_BYTES:
        fail(422, "REPORT_LIMIT", "O relatório excede 8 MiB. Reduza a seleção.")
    manifest["data_sha256"] = hashlib.sha256(canonical(payload)).hexdigest()
    return {"manifest": manifest, "tables": tables, "explanation": explain(tables, sources)}


def explain(tables, sources):
    scenario = tables["scenario"][0]
    paragraphs = [f"A versão {scenario['version']} do cenário considera {scenario['population_count']} pessoas e orçamento de {scenario['effective_budget_minutes']} minutos no mês {scenario['reference_month'][:7]}. Capacidade agregada não garante cobertura simultânea."]
    if tables.get("coverage"):
        row = tables["coverage"][0]
        if row["required_staff_minutes"] is None:
            paragraphs.append(f"A otimização está em {row['state']}; não há cobertura verificada disponível.")
        else:
            paragraphs.append(f"O verificador registra {row['covered_staff_minutes']} de {row['required_staff_minutes']} postos-minuto cobertos, com {row['uncovered_staff_minutes']} descobertos. Isso não aprova juridicamente a proposta.")
    if "finance" in tables:
        paragraphs.append(f"A projeção soma {sum(m['total_cents'] for m in tables['finance'])} centavos BRL em {len(tables['finance'])} meses. O valor depende das premissas da projeção selecionada.")
    if "executions" in tables:
        paragraphs.append(f"Há {len(tables['executions'])} tentativas de automação no mês civil e no escopo autorizado. Retentativas são registros separados.")
    return {"provider": "deterministic", "version": "explanation-1.0", "external_ai_used": False,
        "paragraphs": paragraphs, "sources": sources,
        "limits": "Explicação descritiva. Não altera cálculos, regras, aprovações ou escalas. Sem envio a serviço externo."}
