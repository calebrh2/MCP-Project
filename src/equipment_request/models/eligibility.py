"""Eligibility result for one catalog item."""

from typing import Literal

from pydantic import BaseModel

EligibilityStatus = Literal["eligible", "ineligible", "undetermined"]
EligibilityReason = Literal[
    "issuance_under_max",
    "refresh_elapsed",
    "refresh_not_elapsed",
    "unknown_employee",
    "unknown_role",
    "unlisted_item",
    "incomplete_equipment_record",
]


class Eligibility(BaseModel):
    """Whether one item is inside policy, outside it, or cannot be decided here."""

    employee_id: str
    item: str
    status: EligibilityStatus
    reason_code: EligibilityReason
    role: str | None = None
    units_on_file: int | None = None
    max_on_file: int | None = None
    oldest_assigned_on: str | None = None
    refresh_years: int | None = None
    next_eligible_date: str | None = None
