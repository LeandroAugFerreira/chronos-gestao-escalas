from datetime import date, datetime
from typing import Literal
from pydantic import Field, model_validator
from app.schemas.scheduling import Strict, instant
from app.schemas.simulation import Assumption


class Limits(Assumption):
    max_daily_minutes: int = Field(gt=0, le=1440)
    max_weekly_minutes: int = Field(gt=0, le=10080)
    min_rest_minutes: int = Field(ge=0, le=10080)
    min_break_minutes: int = Field(ge=0, le=240)
    break_threshold_minutes: int = Field(ge=0, le=1440)
    min_weekly_rest_minutes: int = Field(ge=0, le=10080)
    max_consecutive_days: int = Field(ge=1, le=14)


class Template(Strict):
    name: str = Field(min_length=1, max_length=80)
    start_time: str = Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    duration_minutes: int = Field(gt=0, le=1440)
    break_after_minutes: int = Field(default=0, ge=0, le=1440)
    break_minutes: int = Field(default=0, ge=0, le=240)
    break_paid: bool = False
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)), min_length=1, max_length=7)
    cost_cents: int = Field(default=0, ge=0, le=10000000)

    @model_validator(mode="after")
    def valid(self):
        if len(set(self.weekdays)) != len(self.weekdays) or any(d < 0 or d > 6 for d in self.weekdays):
            raise ValueError("Dias inválidos")
        if self.break_minutes and (self.break_after_minutes <= 0 or self.break_after_minutes + self.break_minutes >= self.duration_minutes):
            raise ValueError("Pausa deve ser interna ao plantão")
        return self


class CoverageWindow(Assumption):
    activity_index: int = Field(ge=0, le=29)
    start_at: datetime
    end_at: datetime
    required_staff: int = Field(gt=0, le=500)
    priority: int = Field(default=1, ge=1, le=3)

    @model_validator(mode="after")
    def dates(self):
        self.start_at, self.end_at = instant(self.start_at), instant(self.end_at)
        if self.end_at <= self.start_at:
            raise ValueError("Janela inválida")
        return self


class OptimizationInput(Strict):
    scenario_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=160)
    start_date: date
    end_date: date  # exclusivo
    mode: Literal["strict", "diagnostic"] = "strict"
    eligibility: Literal["verified", "hypothesis"] = "verified"
    templates: list[Template] = Field(min_length=1, max_length=12)
    limits: Limits
    coverage_windows: list[CoverageWindow] = Field(default_factory=list, max_length=50)
    allow_cross_department: bool = False
    activity_job_role_ids: dict[int, list[str]] = Field(default_factory=dict)
    cycle_anchors: dict[str, date] = Field(default_factory=dict)
    history_review_evidence: str = Field(default="", max_length=2000)
    cross_unit_travel_minutes: int = Field(default=0, ge=0, le=1440)
    continuity_max_people_per_activity_day: int | None = Field(default=None, ge=1, le=100)
    parent_schedule_id: str | None = Field(default=None, max_length=36)
    seconds: int = Field(default=20, ge=1, le=120)
    seed: int = Field(default=1042, ge=0, le=2147483647)
    workers: int = Field(default=1, ge=1, le=4)
    balance_weight: int = Field(default=1, ge=0, le=100)
    preference_weight: int = Field(default=1, ge=0, le=100)
    cost_weight: int = Field(default=0, ge=0, le=100)
    cost_source: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def valid(self):
        if not 0 < (self.end_date - self.start_date).days <= 31:
            raise ValueError("Horizonte deve ter até 31 dias com fim exclusivo")
        if (self.cost_weight or any(t.cost_cents for t in self.templates)) and len(self.cost_source) < 5:
            raise ValueError("Informe fonte das estimativas de custos")
        return self


class RevisionInput(Strict):
    revision: int = Field(ge=1)


class DecisionInput(RevisionInput):
    action: Literal["submit", "approve", "reject"]
    schedule_digest: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=10, max_length=2000)


class ReviewInput(Strict):
    kind: Literal["contract", "work_pattern", "qualification", "scenario"]
    entity_id: str = Field(min_length=1, max_length=36)
    entity_digest: str = Field(min_length=64, max_length=64)
    source: str = Field(min_length=5, max_length=2000)
    evidence: str = Field(min_length=20, max_length=4000)
