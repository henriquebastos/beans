# Python imports
from datetime import UTC, datetime
from functools import partial
import re
import secrets
from typing import Literal

# Pip imports
from pydantic import BaseModel, Field


class BeanNotFoundError(KeyError):
    pass


class DepNotFoundError(KeyError):
    pass


class CyclicDepError(ValueError):
    pass


class OpenChildrenError(ValueError):
    pass


ID_BYTES = 4
ID_PATTERN = re.compile(r"^[a-z]+-[0-9a-f]+$")


class BeanId(str):
    pattern = ID_PATTERN

    def __new__(cls, value="", **kwargs):
        if not cls.pattern.match(value):
            raise ValueError(f"Invalid bean id: {value}")
        return super().__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(cls)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        return {"type": "string", "pattern": r"^[a-z]+-[0-9a-f]+$"}

    @classmethod
    def generate(cls, type_name="task", fn=partial(secrets.token_hex, ID_BYTES)) -> BeanId:
        return cls(f"{type_name}-{fn()}")

    @property
    def type_prefix(self) -> str:
        return self.split("-", 1)[0]


class Error(BaseModel):
    message: str


class Dep(BaseModel, frozen=True):
    from_id: BeanId
    to_id: BeanId
    dep_type: str = "blocks"


class Bean(BaseModel):
    id: BeanId = Field(default_factory=BeanId.generate)
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
    close_reason: str | None = None


class BeanUpdate(BaseModel):
    title: str | None = None
    type: str | None = None
    status: Literal["open", "in_progress", "closed"] | None = None
    priority: int | None = Field(default=None, ge=0, le=4)
    body: str | None = None
    parent_id: str | None = None
