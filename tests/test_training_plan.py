"""
Lightweight sanity tests for the training-plan tools.

Verifies URL routing, HTTP method, and body / query-parameter shape per the
OpenAPI spec. Network calls are mocked via monkeypatching
``make_intervals_request`` on the training_plan module.
"""

import asyncio
import os
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.tools.training_plan import (  # noqa: E402
    apply_plan_changes,
    apply_plan_to_calendar,
    change_athlete_plans_bulk,
    change_training_plan,
    get_training_plan,
)


class FakeRequest:
    """Records every call and returns a configurable response."""

    def __init__(self, response: Any = None):
        self.calls: list[dict[str, Any]] = []
        self.response: Any = response if response is not None else {"id": 1}

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self.response

    @property
    def last(self) -> dict[str, Any]:
        return self.calls[-1]


def _patch(monkeypatch, fake: FakeRequest) -> None:
    monkeypatch.setattr("intervals_mcp_server.tools.training_plan.make_intervals_request", fake)


def test_get_training_plan(monkeypatch):
    fake = FakeRequest(response={"training_plan_id": 42})
    _patch(monkeypatch, fake)
    result = asyncio.run(get_training_plan(athlete_id="i1"))
    assert fake.last["url"] == "/athlete/i1/training-plan"
    assert "42" in result


def test_change_training_plan(monkeypatch):
    fake = FakeRequest(response={})
    _patch(monkeypatch, fake)
    asyncio.run(
        change_training_plan(
            athlete_id="i1",
            training_plan_id=99,
            training_plan_start_date="2026-06-01",
            training_plan_alias="Build phase",
        )
    )
    assert fake.last["url"] == "/athlete/i1/training-plan"
    assert fake.last["method"] == "PUT"
    payload = fake.last["data"]
    assert payload["id"] == "i1"
    assert payload["training_plan_id"] == 99
    assert payload["training_plan_start_date"] == "2026-06-01"
    assert payload["training_plan_alias"] == "Build phase"


def test_apply_plan_changes(monkeypatch):
    fake = FakeRequest(response={})
    _patch(monkeypatch, fake)
    asyncio.run(apply_plan_changes(athlete_id="i1"))
    assert fake.last["url"] == "/athlete/i1/apply-plan-changes"
    assert fake.last["method"] == "PUT"


def test_apply_plan_to_calendar(monkeypatch):
    fake = FakeRequest(response={})
    _patch(monkeypatch, fake)
    asyncio.run(
        apply_plan_to_calendar(
            folder_id=123, start_date_local="2026-06-01T00:00:00", athlete_id="i1"
        )
    )
    assert fake.last["url"] == "/athlete/i1/events/apply-plan"
    assert fake.last["method"] == "POST"
    assert fake.last["data"]["folder_id"] == 123
    assert fake.last["data"]["start_date_local"] == "2026-06-01T00:00:00"


def test_change_athlete_plans_bulk(monkeypatch):
    fake = FakeRequest(response={})
    _patch(monkeypatch, fake)
    changes = [
        {"id": "i1", "training_plan_id": 1},
        {"id": "i2", "training_plan_id": 2},
    ]
    asyncio.run(change_athlete_plans_bulk(changes))
    assert fake.last["url"] == "/athlete-plans"
    assert fake.last["method"] == "PUT"
    assert fake.last["data"] == changes
