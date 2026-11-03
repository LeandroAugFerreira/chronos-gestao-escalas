from datetime import UTC, datetime, timedelta
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def instant(value):
    if value.tzinfo is None or value.utcoffset() is None or value.second or value.microsecond:
        raise ValueError("Informe instante com fuso e precisão de minutos")
    return value.astimezone(UTC)


class BreakInput(Strict):
    start_at: datetime
    end_at: datetime
    paid: bool = False

    @model_validator(mode="after")
    def interval(self):
        self.start_at, self.end_at = instant(self.start_at), instant(self.end_at)
        if self.end_at <= self.start_at:
            raise ValueError("Intervalo inválido")
        return self


class ShiftInput(Strict):
    employee_id: str = Field(min_length=1, max_length=36)
    department_id: str = Field(min_length=1, max_length=36)
    start_at: datetime
    end_at: datetime
    label: str = Field(default="Plantão", min_length=1, max_length=80)
    breaks: list[BreakInput] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def interval(self):
        self.start_at, self.end_at = instant(self.start_at), instant(self.end_at)
        if not timedelta(0) < self.end_at - self.start_at <= timedelta(hours=72):
            raise ValueError("Plantão deve durar até 72 horas")
        previous = self.start_at
        for pause in sorted(self.breaks, key=lambda p: p.start_at):
            if pause.start_at < previous or pause.start_at <= self.start_at or pause.end_at >= self.end_at:
                raise ValueError("Pausas sobrepostas ou fora do plantão")
            previous = pause.end_at
        self.breaks.sort(key=lambda p: p.start_at)
        return self


class ShiftSave(ShiftInput):
    preview_digest: str = Field(min_length=64, max_length=64)


class ShiftEdit(ShiftSave):
    revision: int = Field(ge=1)


class CancelInput(Strict):
    revision: int = Field(ge=1)


class RuleInput(Strict):
    key: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_.-]+$")
    version: int = Field(ge=1)
    supersedes_id: str | None = Field(default=None, max_length=36)
    kind: Literal["max_daily", "max_weekly", "min_break", "min_rest", "min_weekly_rest"]
    minutes: int = Field(ge=0, le=10080)
    threshold_minutes: int = Field(default=0, ge=0, le=4320)
    unit_id: str | None = Field(default=None, max_length=36)
    job_role_id: str | None = Field(default=None, max_length=36)
    contract_id: str | None = Field(default=None, max_length=36)
    agreement: str = Field(default="", max_length=200)
    valid_from: datetime
    valid_until: datetime
    source: str = Field(min_length=5, max_length=4000)
    status: Literal["pending_review", "validated"] = "pending_review"
    review_evidence: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def validate_rule(self):
        self.valid_from, self.valid_until = instant(self.valid_from), instant(self.valid_until)
        if self.valid_until <= self.valid_from:
            raise ValueError("Vigência inválida")
        if self.status == "validated" and len(self.review_evidence) < 20:
            raise ValueError("Registre responsável, análise de escopo e evidência da validação")
        return self


class PatternConfiguration(Strict):
    cycle: list[Literal["work", "rest"]] = Field(min_length=1, max_length=62)
    shift_minutes: int = Field(gt=0, le=4320)


class PatternInput(Strict):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=4000)
    configuration: PatternConfiguration | None = None
