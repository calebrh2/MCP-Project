"""Unit tests for flag_for_human_review, called directly rather than over MCP."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from equipment_request import reviews
from equipment_request.models.review_record import ReviewRecord
from equipment_request.reviews import flag_for_human_review

_WHEN = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)


@pytest.fixture
def review_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the escalation log at a temporary file with a fixed clock."""
    path = tmp_path / "reviews.json"
    monkeypatch.setattr(reviews, "_REVIEWS_PATH", path)
    monkeypatch.setattr(reviews, "_now", lambda: _WHEN)
    return path


def test_first_review_is_stored_and_returned(review_log: Path) -> None:
    """The first escalation is R-0001 and the file holds that same record."""
    record = flag_for_human_review(
        "E-1003",
        "The laptop was ruined by a coffee spill and needs replacement.",
        "exception_language",
    )

    assert record == ReviewRecord(
        review_id="R-0001",
        employee_id="E-1003",
        request="The laptop was ruined by a coffee spill and needs replacement.",
        reason="exception_language",
        timestamp="2026-09-30T15:00:00+00:00",
    )
    stored = json.loads(review_log.read_text(encoding="utf-8"))
    assert stored == [record.model_dump()]


def test_second_review_appends_without_replacing_the_first(review_log: Path) -> None:
    """A later call adds R-0002 and leaves the earlier record in place."""
    first = flag_for_human_review("E-1002", "A standing desk.", "unlisted_item")
    second = flag_for_human_review("E-9999", "A headset.", "unknown_employee")

    assert first.review_id == "R-0001"
    assert second.review_id == "R-0002"
    stored = json.loads(review_log.read_text(encoding="utf-8"))
    assert [row["review_id"] for row in stored] == ["R-0001", "R-0002"]
    assert stored[0]["request"] == "A standing desk."
    assert stored[1]["employee_id"] == "E-9999"
