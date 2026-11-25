from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import Field, model_validator
from app.schemas.scheduling import Strict


class TransitionInput(Strict):
    reference_date: date
    contract_weekly_minutes: int = Field(default=2640, gt=0, le=10080)
    planned_weekly_minutes: int = Field(default=2400, ge=0, le=10080)
    planned_daily_minutes: int = Field(default=480, ge=0, le=1440)
    rest_days_24h: int = Field(default=2, ge=0, le=7)
    monthly_salary_cents: int = Field(default=330000, gt=0, le=1_000_000_000)
    proposed_salary_cents: int | None = Field(default=None, gt=0, le=1_000_000_000)
    more_favorable_divisor_hours: Decimal | None = Field(default=None, gt=0, le=1000, max_digits=7, decimal_places=2)
    regime: Literal["regular", "12x36", "rotating", "custom"] = "regular"
    collective_status: Literal["not_reviewed", "present", "absent_at_cutoff"] = "not_reviewed"
    collective_rest_compensation: bool = False
    use_interim_daily_exception: bool = False

    @model_validator(mode="after")
    def supported_date(self):
        if not 2000 <= self.reference_date.year <= 2098:
            raise ValueError("Informe uma data entre 2000 e 2098")
        return self
