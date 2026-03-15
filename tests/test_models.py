# Python imports
import re
from datetime import datetime

# Pip imports
import pytest
from pydantic import ValidationError

# Internal imports
from beans.models import Bean


class TestBeanDefaults:
    """A Bean created with only a title gets sensible defaults."""

    def test_defaults(self):
        bean = Bean(title="Fix auth")

        assert re.fullmatch(r"bean-[0-9a-f]{8}", bean.id)
        assert isinstance(bean.created_at, datetime)
        assert bean.model_dump(exclude={"id", "created_at"}) == {
            "title": "Fix auth",
            "type": "task",
            "status": "open",
            "priority": 2,
            "body": "",
            "parent_id": None,
            "assignee": None,
            "created_by": None,
            "ref_id": None,
        }


class TestBeanCustomFields:
    """A Bean can be created with all fields specified."""

    def test_custom_type(self):
        bean = Bean(title="Design review", type="epic")
        assert bean.type == "epic"

    def test_custom_status(self):
        bean = Bean(title="Done", status="closed")
        assert bean.status == "closed"

    def test_custom_priority(self):
        bean = Bean(title="Urgent", priority=0)
        assert bean.priority == 0

    def test_custom_created_by(self):
        bean = Bean(title="Fix auth", created_by="alice")
        assert bean.created_by == "alice"

    def test_custom_ref_id(self):
        bean = Bean(title="Fix auth", ref_id="GH-123")
        assert bean.ref_id == "GH-123"


class TestBeanValidation:
    """Invalid field values are rejected."""

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            Bean(title="Bad", status="deleted")

    def test_priority_too_high(self):
        with pytest.raises(ValidationError):
            Bean(title="Bad", priority=5)

    def test_priority_too_low(self):
        with pytest.raises(ValidationError):
            Bean(title="Bad", priority=-1)


class TestBeanIdUniqueness:
    """Each Bean gets a unique id."""

    def test_two_beans_have_different_ids(self):
        a = Bean(title="First")
        b = Bean(title="Second")
        assert a.id != b.id
