"""Projeção configurável de 12 meses, centavos e Decimal; não é folha oficial."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
from app.api.dependencies import fail
from app.services.capacity import month_after

CATEGORIES = {"charge", "benefit", "overtime", "night", "hiring", "training", "other"}


def cents(value):
    result = int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if abs(result) > 9_000_000_000_000_000:
        fail(422, "AMOUNT_LIMIT", "Valor excede o limite exato de intercâmbio monetário.")
    return result


def active(component, index):
    return component.start_month <= index <= component.end_month and index in component.month_indexes and (component.recurrence == "monthly" or index == component.start_month)


def project(reference_month, payroll_snapshot, assumptions):
    with localcontext() as ctx:
        ctx.prec = 40
        return calculate(reference_month, payroll_snapshot, assumptions)


def calculate(reference_month, payroll_snapshot, assumptions):
    months, flags = [], set()
    for offset in range(12):
        index = offset + 1
        start, end = month_after(reference_month, offset), month_after(reference_month, offset + 1)
        days = (end - start).days
        payroll, headcount_days, missing_days = 0, 0, 0
        for employee in payroll_snapshot["employees"]:
            covered_dates = set()
            for contract in employee["contracts"]:
                if contract["currency"] != assumptions.currency:
                    fail(422, "CURRENCY_MISMATCH", "Há contrato com moeda diferente da projeção. Conversão cambial não é automática.")
                a = max(start, date.fromisoformat(contract["valid_from"]))
                b = min(end, date.fromisoformat(contract["valid_until"]) if contract["valid_until"] else end)
                if a >= b:
                    continue
                covered = set(range((a - start).days, (b - start).days))
                if covered_dates & covered:
                    fail(422, "AMBIGUOUS_PAYROLL", "Contratos sobrepostos no snapshot impedem uma base salarial inequívoca.")
                covered_dates.update(covered)
                payroll += cents(Decimal(contract["salary_cents"]) * len(covered) / days)
                if contract["validation_status"] != "validated":
                    flags.add("Contratos de origem contêm premissas pendentes de revisão.")
            headcount_days += len(covered_dates)
            missing_days += days - len(covered_dates)
        hire_payroll, hire_count = 0, 0
        for hire in assumptions.new_hires:
            if hire.start_month <= index <= hire.end_month:
                hire_count += hire.headcount
                hire_payroll += hire.monthly_salary_cents * hire.headcount
        base = payroll + hire_payroll
        average_headcount = Decimal(headcount_days) / days + hire_count
        amounts = {}
        quantities = {}
        # As bases percentuais são resolvidas após todas as parcelas de horas, sem depender da ordem.
        for position, component in enumerate(assumptions.components):
            if not active(component, index) or component.kind == "percent":
                continue
            if component.kind == "fixed":
                quantity = average_headcount if component.quantity_basis == "headcount" else Decimal(component.quantity)
                amounts[position] = cents(Decimal(component.amount_cents) * quantity)
                quantities[position] = {"quantity": format(quantity, ".6f")}
            else:
                real = component.real_minutes_by_month[offset]
                payable = Decimal(real) * component.conversion_numerator / component.conversion_denominator
                multiplier = Decimal(component.rate_bps + (10000 if component.include_base_hour else 0)) / 10000
                amounts[position] = cents(Decimal(component.hourly_base_salary_cents) / component.monthly_divisor_minutes * payable * multiplier)
                quantities[position] = {"real_minutes": real, "payable_minutes": format(payable, ".6f"), "multiplier": str(multiplier)}
        overtime = sum(amount for pos, amount in amounts.items() if assumptions.components[pos].category == "overtime")
        night = sum(amount for pos, amount in amounts.items() if assumptions.components[pos].category == "night")
        for position, component in enumerate(assumptions.components):
            if not active(component, index) or component.kind != "percent":
                continue
            basis = {"payroll": base, "overtime": overtime, "night": night, "payroll_and_additions": base + overtime + night}[component.percent_basis]
            amounts[position] = cents(Decimal(basis) * component.rate_bps / 10000)
            quantities[position] = {"basis_cents": basis, "rate_bps": component.rate_bps}
        entries = [{"component_index": position, "name": assumptions.components[position].name, "category": assumptions.components[position].category,
            "amount_cents": amount, **quantities[position]} for position, amount in sorted(amounts.items())]
        total = cents(base + sum(amounts.values()))
        months.append({"index": index, "month": start.isoformat()[:7], "existing_payroll_cents": payroll, "new_hire_payroll_cents": hire_payroll,
            "base_payroll_cents": base, "average_headcount": format(average_headcount, ".6f"), "contract_days_missing": missing_days,
            "components": entries, "total_cents": total})
    included = {c.category for c in assumptions.components}
    excluded = {e.category for e in assumptions.exclusions}
    missing = sorted(CATEGORIES - included - excluded)
    if missing:
        flags.add("Categorias sem parcela ou exclusão justificada: a estimativa é parcial.")
    if any(m["contract_days_missing"] for m in months):
        flags.add("Dias sem contrato válido não foram remunerados; isso não representa desligamento ou economia comprovada.")
    annual_total = cents(sum(month["total_cents"] for month in months))
    annual_categories = {category: cents(sum(entry["amount_cents"] for month in months for entry in month["components"] if entry["category"] == category)) for category in sorted(CATEGORIES)}
    return {"algorithm_version": "financial-1.0", "currency": assumptions.currency, "months": months, "annual_total_cents": annual_total,
        "annual_base_payroll_cents": cents(sum(m["base_payroll_cents"] for m in months)), "annual_components_cents": annual_categories,
        "monthly_average_cents": cents(Decimal(annual_total) / 12), "missing_categories": missing, "validation_status": "pending_review",
        "rounding": "ROUND_HALF_UP por contrato/pessoa/mês e por componente/mês; total soma centavos já arredondados.",
        "source": assumptions.source, "scope": "Projeção de 12 meses com população e contratos congelados; rateio por dias civis é premissa de cálculo.",
        "notices": sorted(flags) + ["Salários contratuais não são reduzidos pela meta de jornada. Alterações futuras de quadro/salário exigem outro snapshot.",
            "Volume de extras/noturno e conversão de minutos são premissas declaradas; não há detecção ou interpretação jurídica automática.",
            "Recorrências, sazonalidade e parcelas únicas são somadas mês a mês; encargos não incidem sobre outros encargos automaticamente.",
            "Novas contratações impactam apenas esta projeção financeira; sua capacidade e habilitações precisam de outra simulação."]}


def difference(left, right):
    delta = right - left
    return {"left": left, "right": right, "delta": delta, "percent": format(Decimal(delta) * 100 / Decimal(left), ".6f") if left else None}
