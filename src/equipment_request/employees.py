"""Employee directory lookup.

Tenure is whole years and leftover months from hire date to 2026-09-30.
"""

import json
import re
from datetime import date
from pathlib import Path

from pydantic import BaseModel, field_validator

from equipment_request.models.employee_info import EmployeeInfo, Tenure
from equipment_request.models.equipment_item import EquipmentItem

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EMPLOYEE_ID = re.compile(r"^E-\d{4}$")
_AS_OF = date(2026, 9, 30)
_DIRECTORY_PATH = Path(__file__).resolve().parent / "data" / "employees.json"


class DirectoryRecord(BaseModel):
    """One row in the mock employee directory."""

    employee_id: str
    name: str
    role: str
    hire_date: str
    equipment: list[EquipmentItem]

    @field_validator("employee_id")
    @classmethod
    def employee_id_format(cls, value: str) -> str:
        """Require the directory key format E-####."""
        if _EMPLOYEE_ID.fullmatch(value) is None:
            raise ValueError("employee_id must match E-####")
        return value

    @field_validator("hire_date")
    @classmethod
    def hire_date_format(cls, value: str) -> str:
        """Require YYYY-MM-DD."""
        if _DATE.fullmatch(value) is None:
            raise ValueError("hire_date must be YYYY-MM-DD")
        return value


def _tenure(hire_date: date, as_of: date = _AS_OF) -> Tenure:
    """Whole years and leftover months from hire_date to as_of."""
    years = as_of.year - hire_date.year
    months = as_of.month - hire_date.month
    if as_of.day < hire_date.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    return Tenure(years=years, months=months)


def _load_directory() -> dict[str, DirectoryRecord]:
    """Read the mock directory keyed by employee id."""
    raw: object = json.loads(_DIRECTORY_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise TypeError("employee directory must be a JSON list")
    records = [DirectoryRecord.model_validate(row) for row in raw]
    return {record.employee_id: record for record in records}


def get_employee_info(employee_id: str) -> EmployeeInfo:
    """Return role, tenure, and equipment on file for an employee.

    Tenure is whole years and leftover months from hire_date to 2026-09-30.
    An unknown id returns found=false and an empty equipment list.
    """
    record = _load_directory().get(employee_id)
    if record is None:
        return EmployeeInfo(employee_id=employee_id, found=False)
    return EmployeeInfo(
        employee_id=record.employee_id,
        found=True,
        name=record.name,
        role=record.role,
        hire_date=record.hire_date,
        tenure=_tenure(date.fromisoformat(record.hire_date)),
        equipment=record.equipment,
    )
