from typing import Literal
from pydantic import Field
from app.schemas.scheduling import Strict


class ReportInput(Strict):
    scenario_id: str = Field(min_length=1, max_length=36)
    optimization_id: str | None = Field(default=None, max_length=36)
    financial_id: str | None = Field(default=None, max_length=36)
    include_people: bool = False


class ExportInput(ReportInput):
    format: Literal["csv", "xlsx"] = "csv"
