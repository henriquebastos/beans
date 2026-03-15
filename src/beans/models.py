# Python imports
from datetime import UTC, datetime
from functools import partial
import secrets
from typing import Literal

# Pip imports
from pydantic import BaseModel, Field

ID_PREFIX = "bean-"
ID_BYTES = 4


class BeanId(str):
    def __new__(cls, value="", **kwargs):
        if not value.startswith(ID_PREFIX):
            raise ValueError(f"Invalid bean id: {value}")
        return super().__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(cls)


def generate_id(prefix=ID_PREFIX, fn=partial(secrets.token_hex, ID_BYTES)) -> BeanId:
    return BeanId(prefix + fn())


class Bean(BaseModel):
    id: BeanId = Field(default_factory=generate_id)
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
