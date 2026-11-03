from datetime import UTC, datetime
from typing import Literal
from uuid import UUID
from pydantic import Field, model_validator
from app.schemas.scheduling import Strict, instant
from app.schemas.phase2 import AvailabilityInput


class Parameters(Strict):
    lookahead_days: int = Field(default=30, ge=1, le=366)
    monitor_limit: int = Field(default=100, ge=1, le=500)
    deliver_n8n: bool = False


class DefinitionPatch(Strict):
    revision: int = Field(ge=1)
    enabled: bool
    owner_id: str | None = Field(default=None, max_length=36)
    interval_minutes: int | None = Field(default=None, ge=1, le=10080)
    parameters: Parameters = Field(default_factory=Parameters)


class QueueAction(Strict):
    revision: int = Field(ge=1)


class CredentialInput(Strict):
    unit_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=160)
    actions: list[Literal["workflow_callback", "availability"]] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.actions)) != len(self.actions):
            raise ValueError("Ações repetidas")
        return self


class CallbackInput(Strict):
    request_id: UUID
    event_id: UUID
    definition_id: UUID
    code: Literal["A02", "A03", "A04", "A06"]
    sent_at: datetime

    @model_validator(mode="after")
    def timestamp(self):
        if self.sent_at.tzinfo is None:
            raise ValueError("Timestamp exige fuso")
        self.sent_at = self.sent_at.astimezone(UTC)
        return self


class IntegratedAvailability(AvailabilityInput):
    request_id: UUID
    sent_at: datetime
    employee_id: str = Field(min_length=1, max_length=36)

    @model_validator(mode="after")
    def timestamp(self):
        if self.sent_at.tzinfo is None:
            raise ValueError("Timestamp exige fuso")
        self.sent_at = self.sent_at.astimezone(UTC)
        return self
