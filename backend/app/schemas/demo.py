"""Contratos públicos do checkpoint da Fase 1."""

from pydantic import BaseModel


class DepartmentSummary(BaseModel):
    id: str
    name: str
    group: str
    operation: str
    employee_count: int
    job_roles: list[str]
    skills: list[str]


class RegimeSummary(BaseModel):
    id: str
    name: str
    description: str
    legal_status: str


class DemoSummary(BaseModel):
    product: str
    version: str
    phase: int
    organization: str
    synthetic: bool
    employee_count: int
    department_count: int
    unit_count: int
    role_count: int
    operation: str
    seed: int
    departments: list[DepartmentSummary]
    regimes: list[RegimeSummary]
    notices: list[str]


class ErrorResponse(BaseModel):
    code: str
    message: str
