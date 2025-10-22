# svh/commands/server/client_api/alerts_schema.py
from pydantic import BaseModel, Field, field_validator
from typing import Literal, List, Optional
from datetime import datetime, timezone
import uuid

Severity = Literal["critical", "high", "medium", "low"]


class AlertIn(BaseModel):
    title: str = Field(min_length=1)
    severity: Severity = "medium"
    source: str = "server"
    description: Optional[str] = None
    tags: List[str] = []


class AlertOut(AlertIn):
    type: Literal["alert"] = "alert"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # if you want to accept UPPERCASE, normalize here:
    @field_validator("severity")
    @classmethod
    def normalize_severity(cls, v: str) -> str:
        return v.lower()  # Literal guard still enforces allowed values
