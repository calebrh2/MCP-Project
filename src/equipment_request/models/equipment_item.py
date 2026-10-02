"""Equipment already assigned to an employee."""

import re

from pydantic import BaseModel, field_validator

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class EquipmentItem(BaseModel):
    """One unit already assigned to an employee."""

    item: str
    assigned_on: str = ""

    @field_validator("assigned_on")
    @classmethod
    def assigned_on_is_date_or_empty(cls, value: str) -> str:
        """Accept a calendar date or a blank when the record has no date."""
        if value and _DATE.fullmatch(value) is None:
            raise ValueError("assigned_on must be YYYY-MM-DD or empty")
        return value
