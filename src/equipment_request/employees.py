"""Directory models returned by employee lookup.

Tenure is measured against the fixed evaluation date 2026-09-30.
"""

import re
from typing import Self

from pydantic import BaseModel, field_validator, model_validator

from equipment_request.models.equipment_item import EquipmentItem

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EMPLOYEE_ID = re.compile(r"^E-\d{4}$")


class Tenure(BaseModel):
    """Whole years and leftover months from hire date to 2026-09-30."""

    years: int
    months: int

    @field_validator("years", "months")
    @classmethod
    def non_negative(cls, value: int) -> int:
        """Reject a negative span."""
        if value < 0:
            raise ValueError("tenure must be non-negative")
        return value

    @field_validator("months")
    @classmethod
    def months_in_range(cls, value: int) -> int:
        """Keep leftover months inside a single year."""
        if value > 11:
            raise ValueError("months must be 0 through 11")
        return value


class EmployeeInfo(BaseModel):
    """Employee directory record, or a not-found result for an unknown id."""

    employee_id: str
    found: bool
    name: str | None = None
    role: str | None = None
    hire_date: str | None = None
    tenure: Tenure | None = None
    equipment: list[EquipmentItem] = []

    @field_validator("employee_id")
    @classmethod
    def employee_id_format(cls, value: str) -> str:
        """Require the directory key format E-####."""
        if _EMPLOYEE_ID.fullmatch(value) is None:
            raise ValueError("employee_id must match E-####")
        return value

    @field_validator("hire_date")
    @classmethod
    def hire_date_format(cls, value: str | None) -> str | None:
        """Require YYYY-MM-DD when a hire date is present."""
        if value is not None and _DATE.fullmatch(value) is None:
            raise ValueError("hire_date must be YYYY-MM-DD")
        return value

    @model_validator(mode="after")
    def found_record_is_complete(self) -> Self:
        """A located employee has identity fields; an unknown id has no equipment."""
        if self.found:
            missing = [
                name
                for name in ("name", "role", "hire_date", "tenure")
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(
                    "a found employee requires " + ", ".join(missing)
                )
        elif self.equipment:
            raise ValueError("an unknown employee has an empty equipment list")
        return self
