"""Chronos 2.0: dated planning references, never a legal certification.

The 1.0 scheduling engine and its persisted rule versions remain reproducible.
This module is an explicit comparison of declared planning assumptions. It does
not infer collective agreements, qualifying employee exceptions or rest history.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json

POLICY_VERSION = "br-ec141-2026.11.25"
REVIEW_DATE = "2026-11-25"
SOURCES = [
    {"id": "ec141", "title": "EC 141/2026", "url": "https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc141.htm", "articles": "arts. 1º, 2º, 4º, 6º, 7º e 8º"},
    {"id": "decree13173", "title": "Decreto 13.173/2026", "url": "https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2026/decreto/d13173.htm", "articles": "arts. 2º, 3º, 5º e 7º"},
    {"id": "portaria2041", "title": "Portaria MTE 2.041/2026", "url": "https://www.in.gov.br/web/dou/-/portaria-mte-n-2.041-de-19-de-novembro-de-2026-745783275", "articles": "arts. 3º, 6º a 10; publicação de 23/11/2026; observar retificação e decisões judiciais"},
    {"id": "stf8041", "title": "STF · cautelar nas ADIs 8.041 e 8.042", "url": "https://portal.stf.jus.br/processos/downloadPeca.asp?ext=.pdf&id=15392248509", "articles": "decisão de 12/11/2026, dispositivo, itens I, IV, VII e VIII; interpretação sujeita à evolução do processo"},
]
PHASES = (
    {"id": "historical_44", "name": "Referência anterior à transição", "from": "2000-01-01", "until": "2026-12-16", "weekly_minutes": 2640, "rest_days": 1, "monthly_divisor_hours": 220},
    {"id": "transition_42", "name": "Etapa de 42 horas", "from": "2026-12-16", "until": "2027-12-16", "weekly_minutes": 2520, "rest_days": 2, "monthly_divisor_hours": 210},
    {"id": "final_40", "name": "Etapa de 40 horas", "from": "2027-12-16", "until": None, "weekly_minutes": 2400, "rest_days": 2, "monthly_divisor_hours": 200},
)


def metadata():
    return {"product_version": "2.0", "policy_version": POLICY_VERSION, "reviewed_on": REVIEW_DATE,
            "phases": [dict(p) for p in PHASES], "sources": [dict(s) for s in SOURCES],
            "scope": "Comparação de premissas declaradas. Regimes especiais, normas coletivas, decisões judiciais e histórico de descansos exigem revisão. Não certifica conformidade nem altera escalas ou regras já gravadas."}


def reference(on: date):
    return dict(next(p for p in reversed(PHASES) if on >= date.fromisoformat(p["from"])))


def money(value):
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def compare(payload):
    """Return reproducible comparisons; amounts are integer cents/Decimal."""
    facts = payload.model_dump(mode="json")
    phase = reference(payload.reference_date)
    contract_minutes = payload.contract_weekly_minutes
    effective_minutes = min(contract_minutes, phase["weekly_minutes"])
    # Weekly-to-monthly divisor is a declared ordinary-hours reference. A lower
    # contractual/collective divisor prevails; this is not total monthly capacity.
    contract_divisor = Decimal(contract_minutes) / Decimal(12)
    divisor = min(contract_divisor, Decimal(phase["monthly_divisor_hours"]))
    if payload.more_favorable_divisor_hours is not None:
        divisor = min(divisor, payload.more_favorable_divisor_hours)
    hourly = Decimal(payload.monthly_salary_cents) / divisor
    baseline_hourly = Decimal(payload.monthly_salary_cents) / contract_divisor
    findings = []

    def add(code, status, message, sources):
        findings.append({"code": code, "status": status, "message": message, "source_ids": sources})

    special = payload.regime != "regular"
    if special:
        add("SPECIAL_REGIME", "review", "Regime especial: conferir lei específica, contrato e instrumento coletivo. Em 12x36, excesso da média mensal exige compensação ou pagamento conforme o instrumento aplicável; o limite diário comum não é aplicado automaticamente.", ["decree13173", "portaria2041"])
    else:
        add("WEEKLY_LIMIT", "exceeds" if payload.planned_weekly_minutes > effective_minutes else "within", "Comparação da carga semanal declarada com o menor limite entre contrato e etapa normativa.", ["ec141"])
        if not payload.collective_rest_compensation and payload.planned_weekly_minutes > payload.planned_daily_minutes * (7 - payload.rest_days_24h):
            add("DECLARED_CAPACITY", "exceeds", "A carga semanal declarada não cabe na quantidade de dias de trabalho e na maior jornada diária informadas. Revise as premissas; limites isolados não comprovam viabilidade de uma escala.", ["ec141"])
        daily_limit = 480
        if payload.use_interim_daily_exception:
            if phase["id"] == "transition_42" and payload.collective_status == "absent_at_cutoff":
                daily_limit = 504
                add("INTERIM_DAILY_EXCEPTION", "review", "Hipótese explícita da cautelar do STF: ausência de ACT/CCT até 15/12/2026, distribuição em cinco dias e até 8h24 líquidas por dia somente durante a transição. Conferir vigência da decisão e enquadramento antes de adotar.", ["stf8041"])
            else:
                add("INTERIM_DAILY_EXCEPTION", "review", "A exceção de 8h24 não foi aplicada: data ou situação da negociação coletiva não satisfazem a hipótese declarada da cautelar.", ["stf8041"])
        add("DAILY_LIMIT", "exceeds" if payload.planned_daily_minutes > daily_limit else "within", f"Referência diária para esta simulação: {daily_limit} minutos líquidos. Compensação diversa exige análise do instrumento aplicável.", ["ec141", "stf8041"])
    if payload.collective_rest_compensation or special:
        add("REST_REVIEW", "review", "Distribuição compensada ou regime especial: revisar o instrumento coletivo, a íntegra da cautelar e a regulamentação. Não concluir pela simples contagem semanal; períodos sem histórico não comprovam descanso.", ["ec141", "stf8041", "portaria2041"])
    else:
        add("WEEKLY_RESTS", "exceeds" if payload.rest_days_24h < phase["rest_days"] else "within", f"Referência: {phase['rest_days']} repouso(s) semanal(is) de 24 horas. Dois repousos não significam necessariamente 48 horas consecutivas; interjornada e histórico são verificações próprias.", ["ec141", "portaria2041"])
    if payload.proposed_salary_cents is not None and payload.proposed_salary_cents < payload.monthly_salary_cents:
        add("SALARY_PRESERVATION", "exceeds", "A redução salarial proposta não foi aplicada ao cálculo. A transição preserva o salário mensal e os pisos dos contratos abrangidos.", ["ec141"])
    else:
        add("SALARY_PRESERVATION", "within", "Salário mensal preservado na comparação; o valor da hora pode mudar com o divisor.", ["ec141", "decree13173"])
    if contract_minutes <= 2400:
        add("SHORTER_CONTRACT", "within", "Contrato já igual ou inferior a 40 horas: sem redução proporcional automática da carga contratada.", ["ec141"])
    add("SCOPE_REVIEW", "review", "Resultado de planejamento, sem aprovação jurídica automática. Verificar pausas, interjornada, trabalho noturno, domingos, qualificações, enquadramento e instrumentos coletivos antes de usar uma escala.", ["ec141", "decree13173", "portaria2041", "stf8041"])
    if payload.reference_date > date.fromisoformat(REVIEW_DATE):
        add("FUTURE_REFERENCE", "review", "Projeção com as fontes verificadas em 25/11/2026. Conferir atos posteriores antes da data de aplicação.", ["ec141", "stf8041"])
    result = {"product_version": "2.0", "policy_version": POLICY_VERSION, "reviewed_on": REVIEW_DATE,
              "phase": phase, "assumptions": facts,
              "effective_weekly_minutes": effective_minutes,
              "monthly_divisor_hours": format(divisor.normalize(), "f"),
              "monthly_salary_cents": payload.monthly_salary_cents,
              "baseline_hourly_cents": money(baseline_hourly), "hourly_cents": money(hourly),
              "hourly_change_percent": str(((hourly / baseline_hourly - 1) * 100).quantize(Decimal("0.01"))),
              "baseline_version": "1.0", "baseline_contract_weekly_minutes": contract_minutes,
              "status": "adjustment_required" if any(f["status"] == "exceeds" for f in findings) else "review_required",
              "findings": findings, "sources": [dict(s) for s in SOURCES]}
    result["digest"] = hashlib.sha256(json.dumps(result, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return result
