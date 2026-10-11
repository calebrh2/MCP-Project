"""One escalated equipment request waiting for a person."""

import re
from datetime import datetime

from pydantic import BaseModel, field_validator

_REVIEW_ID = re.compile(r"^R-\d{4}$")


class ReviewRecord(BaseModel):
    """A recorded escalation. It does not approve or deny the request."""

    review_id: str
    employee_id: str
    request: str
    reason: str
    timestamp: str

    @field_validator("review_id")
    @classmethod
    def review_id_format(cls, value: str) -> str:
        """Require the log key format R-####."""
        if _REVIEW_ID.fullmatch(value) is None:
            raise ValueError("review_id must match R-####")
        return value

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_iso(cls, value: str) -> str:
        """Require an ISO-8601 timestamp."""
        datetime.fromisoformat(value)
        return value
