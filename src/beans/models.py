# Python imports
from datetime import UTC, datetime
from functools import partial
import secrets
from typing import Literal

# Pip imports
from pydantic import BaseModel, Field


class BeanNotFoundError(KeyError):
    pass


ID_PREFIX = "bean-"
ID_BYTES = 4


class BeanId(str):
    prefix = ID_PREFIX

    def __new__(cls, value="", **kwargs):
        if not value.startswith(cls.prefix):
            raise ValueError(f"Invalid bean id: {value}")
        return super().__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(cls)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        return {"type": "string", "pattern": f"^{cls.prefix}[0-9a-f]{{8}}$"}

    @classmethod
    def generate(cls, prefix=ID_PREFIX, fn=partial(secrets.token_hex, ID_BYTES)) -> BeanId:
        return cls(prefix + fn())


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

    @classmethod
    def fields_validate(cls, **fields):
        cls.model_validate({"id": "bean-00000000", "title": "validate", **fields})
