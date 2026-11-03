from datetime import date, time
from typing import Literal
from pydantic import Field, model_validator
from app.schemas.scheduling import Strict

Category = Literal["charge", "benefit", "overtime", "night", "hiring", "training", "other"]


class Assumption(Strict):
    source: str = Field(min_length=5, max_length=2000)
    validation_status: Literal["pending_review", "validated"] = "pending_review"
    review_evidence: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def reviewed(self):
        if self.validation_status == "validated" and len(self.review_evidence) < 20:
            raise ValueError("Registre responsável, condições e evidência de revisão")
        return self


class DemandInput(Assumption):
    name: str = Field(min_length=1, max_length=160)
    department_id: str = Field(min_length=1, max_length=36)
    start_time: str = Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    duration_minutes: int = Field(gt=0, le=1440)
    weekdays: list[int] = Field(min_length=1, max_length=7)
    required_staff: int = Field(ge=0, le=500)
    skill_ids: list[str] = Field(default_factory=list, max_length=20)
    qualification_ids: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def days(self):
        if len(set(self.weekdays)) != len(self.weekdays) or any(day < 0 or day > 6 for day in self.weekdays):
            raise ValueError("Dias da semana inválidos")
        return self


class ScenarioInput(Assumption):
    unit_id: str = Field(min_length=1, max_length=36)
    department_id: str | None = Field(default=None, max_length=36)
    key: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_.-]+$")
    version: int = Field(default=1, ge=1)
    parent_id: str | None = Field(default=None, max_length=36)
    name: str = Field(min_length=1, max_length=160)
    reference_month: date
    mode: Literal["calendar", "cycle"] = "calendar"
    work_pattern_id: str | None = Field(default=None, max_length=36)
    cycle_anchor: date | None = None
    start_time: str = Field(default="08:00", pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    break_minutes: int = Field(default=0, ge=0, le=240)
    target_weekly_minutes: int | None = Field(default=None, gt=0, le=10080)
    eligibility: Literal["verified", "hypothesis"] = "verified"
    demands: list[DemandInput] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def scope(self):
        if self.reference_month.day != 1 or not 2000 <= self.reference_month.year <= 2098:
            raise ValueError("Mês de referência deve iniciar no dia 1, entre 2000 e 2098")
        if self.mode == "cycle" and (not self.work_pattern_id or not self.cycle_anchor):
            raise ValueError("Informe regime e âncora do ciclo")
        if self.parent_id is None and self.version != 1:
            raise ValueError("Primeira versão deve ser 1")
        return self


class NewHire(Assumption):
    headcount: int = Field(gt=0, le=500)
    monthly_salary_cents: int = Field(gt=0, le=1_000_000_000)
    start_month: int = Field(default=1, ge=1, le=12)
    end_month: int = Field(default=12, ge=1, le=12)

    @model_validator(mode="after")
    def dates(self):
        if self.end_month < self.start_month:
            raise ValueError("Vigência de contratação inválida")
        return self


class CostComponent(Assumption):
    name: str = Field(min_length=1, max_length=160)
    category: Category
    kind: Literal["fixed", "percent", "hours"]
    recurrence: Literal["monthly", "once"] = "monthly"
    start_month: int = Field(default=1, ge=1, le=12)
    end_month: int = Field(default=12, ge=1, le=12)
    month_indexes: list[int] = Field(default_factory=lambda: list(range(1, 13)), min_length=1, max_length=12)
    amount_cents: int = Field(default=0, ge=0, le=1_000_000_000)
    quantity: int = Field(default=1, ge=0, le=10000)
    quantity_basis: Literal["units", "headcount"] = "units"
    rate_bps: int = Field(default=0, ge=0, le=100000)
    percent_basis: Literal["payroll", "overtime", "night", "payroll_and_additions"] = "payroll"
    hourly_base_salary_cents: int = Field(default=0, ge=0, le=1_000_000_000)
    monthly_divisor_minutes: int = Field(default=1, ge=1, le=100000)
    real_minutes_by_month: list[int] = Field(default_factory=lambda: [0] * 12, min_length=12, max_length=12)
    conversion_numerator: int = Field(default=1, ge=1, le=1000)
    conversion_denominator: int = Field(default=1, ge=1, le=1000)
    include_base_hour: bool = False

    @model_validator(mode="after")
    def valid_component(self):
        if self.end_month < self.start_month or len(set(self.month_indexes)) != len(self.month_indexes) or any(i < 1 or i > 12 for i in self.month_indexes):
            raise ValueError("Vigência/sazonalidade inválida")
        if any(m < 0 or m > 10_000_000 for m in self.real_minutes_by_month):
            raise ValueError("Volume de horas inválido")
        if self.kind == "hours" and (self.hourly_base_salary_cents <= 0 or self.category not in {"overtime", "night"}):
            raise ValueError("Horas exigem salário/divisor explícitos e categoria extra/noturna")
        if self.kind == "hours" and "monthly_divisor_minutes" not in self.model_fields_set:
            raise ValueError("Informe explicitamente o divisor mensal aplicável")
        if self.category in {"overtime", "night"} and self.kind != "hours":
            raise ValueError("Extras/noturno exigem modelo de horas e bases explícitas")
        if self.recurrence == "once" and self.start_month not in self.month_indexes:
            raise ValueError("Parcela única deve incluir seu mês inicial")
        return self


class ExcludedCategory(Assumption):
    category: Category
    justification: str = Field(min_length=10, max_length=1000)


class FinancialInput(Assumption):
    scenario_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=160)
    currency: Literal["BRL"] = "BRL"
    proration: Literal["calendar_days"] = "calendar_days"
    components: list[CostComponent] = Field(default_factory=list, max_length=50)
    new_hires: list[NewHire] = Field(default_factory=list, max_length=12)
    exclusions: list[ExcludedCategory] = Field(default_factory=list, max_length=7)

    @model_validator(mode="after")
    def exclusions_unique(self):
        excluded = [e.category for e in self.exclusions]
        if len(set(excluded)) != len(excluded) or set(excluded) & {c.category for c in self.components}:
            raise ValueError("Categoria duplicada ou simultaneamente incluída/excluída")
        return self


class ComparisonInput(Strict):
    left_id: str = Field(min_length=1, max_length=36)
    right_id: str = Field(min_length=1, max_length=36)
