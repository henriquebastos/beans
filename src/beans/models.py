# Python imports
import datetime
import secrets
from typing import Literal

# Pip imports
from pydantic import BaseModel, Field


def _generate_bean_id() -> str:
    return "bean-" + secrets.token_hex(4)


class Bean(BaseModel):
    id: str = Field(default_factory=_generate_bean_id)
    title: str
    type: str = "task"
    status: Literal["open", "in_progress", "closed"] = "open"
    priority: int = Field(default=2, ge=0, le=4)
    body: str = ""
    labels: list[str] = Field(default_factory=list)
    parent_id: str | None = None
    assignee: str | None = None
    created_by: str | None = None
    ref_id: str | None = None
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
