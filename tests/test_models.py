# Python imports
from datetime import UTC, datetime
import re

from pydantic import ValidationError

# Pip imports
import pytest

from beans.models import Bean, BeanId, Error

FIXED_TIME = datetime(2025, 1, 1, tzinfo=UTC)


class TestBeanDefaults:
    """A Bean created with only a title gets sensible defaults."""

    def test_defaults(self):
        bean = Bean(id="bean-00000000", title="Fix auth", created_at=FIXED_TIME)

        assert bean.model_dump() == {
            "id": "bean-00000000",
            "title": "Fix auth",
            "type": "task",
            "status": "open",
            "priority": 2,
            "body": "",
            "parent_id": None,
            "assignee": None,
            "created_by": None,
            "ref_id": None,
            "created_at": FIXED_TIME,
            "closed_at": None,
            "close_reason": None,
        }

    def test_id_format(self):
        bean = Bean(title="Fix auth")
        assert re.fullmatch(r"bean-[0-9a-f]{8}", bean.id)

    def test_created_at_is_set(self):
        bean = Bean(title="Fix auth")
        assert isinstance(bean.created_at, datetime)


class TestBeanCustomFields:
    """A Bean can be created with all fields specified."""

    def test_custom_type(self):
        bean = Bean(title="Design review", type="epic")
        assert bean.type == "epic"

    def test_review_type(self):
        bean = Bean(title="Review migration plan", type="review")
        assert bean.type == "review"

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

    def test_invalid_type(self):
        with pytest.raises(ValidationError):
            Bean(title="Bad", type="invalid")


class TestErrorModel:
    """Error model for structured error output."""

    def test_error_from_message(self):
        err = Error(message="not found")
        assert err.model_dump() == {"message": "not found"}


class TestBeanId:
    """BeanId validates prefix and generates unique ids."""

    def test_two_beans_have_different_ids(self):
        a = Bean(title="First")
        b = Bean(title="Second")
        assert a.id != b.id

    def test_accepts_prefix_for_matching(self):
        bid = BeanId("bean-a3")
        assert bid == "bean-a3"

    def test_rejects_missing_prefix(self):
        with pytest.raises(ValueError, match="Invalid bean id"):
            BeanId("not-a-bean")
