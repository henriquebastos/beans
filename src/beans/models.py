# Python imports
from datetime import UTC, datetime
from functools import partial
import secrets
from typing import Literal

# Pip imports
from pydantic import BaseModel, Field

ID_BYTES = 4


def generate_id(prefix="bean-", fn=partial(secrets.token_hex, ID_BYTES)) -> str:
    return prefix + fn()


class Bean(BaseModel):
    id: str = Field(default_factory=generate_id)
    title: str
    type: str = "task"
    status: Literal["open", "in_progress", "closed"] = "open"
    priority: int = Field(default=2, ge=0, le=4)
    body: str = ""
    parent_id: str | None = None
    assignee: str | None = None
    created_by: str | None = None
    ref_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    closed_at: datetime | None = None
