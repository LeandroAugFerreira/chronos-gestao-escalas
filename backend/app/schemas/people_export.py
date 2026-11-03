from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class PeopleExportInput(BaseModel):
    # Preserve the search exactly as in GET /employees, including whitespace.
    model_config = ConfigDict(extra="forbid")
    unit_id: str | None = Field(default=None, min_length=1, max_length=36)
    department_id: str | None = Field(default=None, min_length=1, max_length=36)
    status: Literal["active", "inactive"] | None = None
    search: str = Field(default="", max_length=120)
    sort: Literal["name", "registration", "status"] = "name"
    descending: bool = False
