"""Escalation log for requests a person must review.

Each call appends one record. The record does not approve or deny the request.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from equipment_request.models.review_record import ReviewRecord

_REVIEWS_PATH = Path(__file__).resolve().parent / "data" / "reviews.json"


def _now() -> datetime:
    """Current UTC time. Tests replace this so timestamps stay fixed."""
    return datetime.now(UTC)


def _load_reviews() -> list[ReviewRecord]:
    """Read the escalation log, or an empty list when none has been written."""
    if not _REVIEWS_PATH.exists():
        return []
    raw: object = json.loads(_REVIEWS_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise TypeError("review log must be a JSON list")
    return [ReviewRecord.model_validate(row) for row in raw]


def _save_reviews(reviews: list[ReviewRecord]) -> None:
    """Replace the escalation log with these records."""
    payload = [review.model_dump() for review in reviews]
    _REVIEWS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def flag_for_human_review(employee_id: str, request: str, reason: str) -> ReviewRecord:
    """Append one escalation and return the new review record.

    The review id is the next R-#### in the log. The call does not approve
    or deny the request.
    """
    reviews = _load_reviews()
    record = ReviewRecord(
        review_id=f"R-{len(reviews) + 1:04d}",
        employee_id=employee_id,
        request=request,
        reason=reason,
        timestamp=_now().isoformat(),
    )
    reviews.append(record)
    _save_reviews(reviews)
    return record
