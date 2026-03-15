# Python imports
import re
from datetime import datetime, timezone

# Pip imports
import pytest
from pydantic import ValidationError

# Internal imports
from beans.models import Bean


class TestBeanDefaults:
    """A Bean created with only a title gets sensible defaults."""

    @pytest.fixture()
    def bean(self):
        return Bean(title="Fix auth")

    def test_id_format(self, bean):
        assert re.fullmatch(r"bean-[0-9a-f]{8}", bean.id)

    def test_title(self, bean):
        assert bean.title == "Fix auth"

    def test_type_defaults_to_task(self, bean):
        assert bean.type == "task"

    def test_status_defaults_to_open(self, bean):
        assert bean.status == "open"

    def test_priority_defaults_to_2(self, bean):
        assert bean.priority == 2

    def test_body_defaults_to_empty(self, bean):
        assert bean.body == ""

    def test_labels_defaults_to_empty(self, bean):
        assert bean.labels == []

    def test_parent_id_defaults_to_none(self, bean):
        assert bean.parent_id is None

    def test_assignee_defaults_to_none(self, bean):
        assert bean.assignee is None

    def test_created_by_defaults_to_none(self, bean):
        assert bean.created_by is None

    def test_ref_id_defaults_to_none(self, bean):
        assert bean.ref_id is None

    def test_created_at_is_set(self, bean):
        assert isinstance(bean.created_at, datetime)


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
