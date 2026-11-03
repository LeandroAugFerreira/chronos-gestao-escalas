from datetime import UTC, date, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginInput(Input):
    organization: str = Field(min_length=1, max_length=80)
    username: str = Field(min_length=1, max_length=80)
    password: SecretStr = Field(min_length=1, max_length=128)


class RefreshInput(Input):
    refresh_token: SecretStr = Field(min_length=32, max_length=256)


class UnitInput(Input):
    name: str = Field(min_length=2, max_length=160)
    operation: str = Field(default="business", min_length=1, max_length=32)
    timezone: str = "America/Sao_Paulo"

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Fuso IANA inválido")
        return value


class DepartmentInput(Input):
    unit_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=2, max_length=160)
    group: str = Field(min_length=1, max_length=80)
    operation: str = Field(default="business", min_length=1, max_length=32)
    cost_center: str = Field(default="", max_length=80)


class CatalogInput(Input):
    name: str = Field(min_length=2, max_length=160)


class EmployeeInput(Input):
    unit_id: str = Field(min_length=1, max_length=36)
    department_id: str = Field(min_length=1, max_length=36)
    job_role_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=2, max_length=160)
    registration: str = Field(min_length=1, max_length=40)
    synthetic: Literal[True] = True


class EmployeePatch(Input):
    revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    status: Literal["active", "inactive"] | None = None
    unit_id: str | None = Field(default=None, min_length=1, max_length=36)
    department_id: str | None = Field(default=None, min_length=1, max_length=36)
    job_role_id: str | None = Field(default=None, min_length=1, max_length=36)

    @model_validator(mode="after")
    def nonempty_patch(self):
        if all(getattr(self, key) is None for key in ["name", "status", "unit_id", "department_id", "job_role_id"]):
            raise ValueError("Informe uma alteração")
        if bool(self.unit_id) != bool(self.department_id):
            raise ValueError("Informe unidade e setor juntos ao alterar lotação")
        return self


class UnitPatch(UnitInput):
    revision: int = Field(ge=1)


class DepartmentPatch(DepartmentInput):
    revision: int = Field(ge=1)


class CatalogPatch(CatalogInput):
    revision: int = Field(ge=1)


class ContractInput(Input):
    work_pattern_id: str = Field(min_length=1, max_length=36)
    weekly_minutes: int = Field(gt=0, le=10080)
    base_salary_cents: int = Field(ge=0, le=2147483647)
    employment_type: str = Field(min_length=1, max_length=40)
    valid_from: date
    valid_until: date | None = None
    assumption_source: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def dates(self):
        if self.valid_until and self.valid_until <= self.valid_from:
            raise ValueError("Fim deve ser posterior ao início")
        return self


class QualificationInput(Input):
    qualification_id: str = Field(min_length=1, max_length=36)
    valid_from: date
    valid_until: date
    evidence: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def dates(self):
        if self.valid_until <= self.valid_from:
            raise ValueError("Fim deve ser posterior ao início")
        return self


class SkillInput(Input):
    skill_id: str = Field(min_length=1, max_length=36)


class AvailabilityInput(Input):
    start_at: datetime
    end_at: datetime
    type: Literal["available", "unavailable"] = "unavailable"
    reason: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def dates(self):
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None or self.end_at <= self.start_at:
            raise ValueError("Use instantes com fuso e fim posterior ao início")
        self.start_at = self.start_at.astimezone(UTC)
        self.end_at = self.end_at.astimezone(UTC)
        return self


class UserInput(Input):
    username: str = Field(pattern=r"^[a-z0-9][a-z0-9._@+-]{2,79}$")
    password: SecretStr = Field(min_length=12, max_length=128)
    role: Literal["admin", "hr", "manager", "finance", "analyst", "demo"]
    unit_id: str | None = Field(default=None, max_length=36)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"]
    expires_in: int


class MeResponse(BaseModel):
    id: str
    username: str
    organization_id: str
    permissions: dict[str, list[str] | None]


class EmployeeOutput(BaseModel):
    id: str
    organization_id: str
    unit_id: str
    department_id: str
    job_role_id: str
    name: str
    registration: str
    status: Literal["active", "inactive"]
    synthetic: bool
    revision: int


class EmployeePage(BaseModel):
    items: list[EmployeeOutput]
    total: int
    page: int
    page_size: int
