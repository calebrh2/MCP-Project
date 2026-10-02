"""Unit tests for get_employee_info, called directly rather than over MCP."""

from datetime import date

from equipment_request.employees import _tenure, get_employee_info
from equipment_request.models.employee_info import EmployeeInfo
from equipment_request.models.equipment_item import EquipmentItem


def test_known_employee_includes_role_tenure_and_equipment() -> None:
    """A directory hit returns role, tenure as of 2026-09-30, and equipment."""
    info = get_employee_info("E-1001")

    assert info.found is True
    assert info.name == "Alex Chen"
    assert info.role == "individual_contributor"
    assert info.hire_date == "2022-01-15"
    assert info.tenure is not None
    assert info.tenure.years == 4
    assert info.tenure.months == 8
    assert info.equipment == [
        EquipmentItem(item="laptop", assigned_on="2022-02-01"),
        EquipmentItem(item="monitor", assigned_on="2025-06-01"),
        EquipmentItem(item="headset", assigned_on="2025-01-10"),
    ]


def test_unknown_employee_is_not_found() -> None:
    """An id absent from the directory is a not-found result with no equipment."""
    info = get_employee_info("E-9999")

    assert info == EmployeeInfo(employee_id="E-9999", found=False)


def test_tenure_on_anniversary_has_zero_leftover_months() -> None:
    """A hire date on the evaluation month and day is a whole number of years."""
    info = get_employee_info("E-1007")

    assert info.tenure is not None
    assert (info.tenure.years, info.tenure.months) == (8, 0)


def test_tenure_counts_a_partial_year() -> None:
    """Months before the next anniversary stay in the leftover-month field."""
    info = get_employee_info("E-1005")

    assert info.tenure is not None
    assert (info.tenure.years, info.tenure.months) == (0, 10)


def test_missing_assignment_date_is_preserved() -> None:
    """A blank assigned_on on file is returned unchanged."""
    info = get_employee_info("E-1006")

    assert info.found is True
    monitors = [item for item in info.equipment if item.item == "monitor"]
    assert monitors == [EquipmentItem(item="monitor", assigned_on="")]


def test_tenure_borrows_a_month_before_the_anniversary_day() -> None:
    """The year does not advance until the hire day in that month."""
    tenure = _tenure(date(2022, 9, 15), date(2026, 9, 1))

    assert (tenure.years, tenure.months) == (3, 11)
