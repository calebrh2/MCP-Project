"""Unit tests for check_request_eligibility, called directly rather than over MCP."""

from equipment_request.eligibility import check_request_eligibility
from equipment_request.models.eligibility import Eligibility


def test_laptop_refresh_is_eligible_when_the_interval_has_elapsed() -> None:
    """E-1001's laptop from 2022-02-01 passed the four-year refresh on 2026-02-01."""
    result = check_request_eligibility("E-1001", "laptop")

    assert result == Eligibility(
        employee_id="E-1001",
        item="laptop",
        status="eligible",
        reason_code="refresh_elapsed",
        role="individual_contributor",
        units_on_file=1,
        max_on_file=1,
        oldest_assigned_on="2022-02-01",
        refresh_years=4,
        next_eligible_date="2026-02-01",
    )


def test_second_monitor_is_an_issuance_under_the_manager_cap() -> None:
    """E-1002 holds one monitor and a manager may hold two."""
    result = check_request_eligibility("E-1002", "monitor")

    assert result == Eligibility(
        employee_id="E-1002",
        item="monitor",
        status="eligible",
        reason_code="issuance_under_max",
        role="manager",
        units_on_file=1,
        max_on_file=2,
        oldest_assigned_on="2023-01-15",
        refresh_years=3,
    )


def test_first_dock_is_an_issuance_with_no_assignment_date() -> None:
    """A catalog item the employee does not hold yet has no oldest date."""
    result = check_request_eligibility("E-1001", "docking_station")

    assert result == Eligibility(
        employee_id="E-1001",
        item="docking_station",
        status="eligible",
        reason_code="issuance_under_max",
        role="individual_contributor",
        units_on_file=0,
        max_on_file=1,
        refresh_years=4,
    )


def test_manager_laptop_refresh_is_eligible_after_two_years() -> None:
    """E-1004's laptop from 2023-05-01 passed the two-year refresh on 2025-05-01."""
    result = check_request_eligibility("E-1004", "laptop")

    assert result == Eligibility(
        employee_id="E-1004",
        item="laptop",
        status="eligible",
        reason_code="refresh_elapsed",
        role="manager",
        units_on_file=1,
        max_on_file=1,
        oldest_assigned_on="2023-05-01",
        refresh_years=2,
        next_eligible_date="2025-05-01",
    )


def test_oldest_of_two_monitors_drives_the_director_refresh() -> None:
    """E-1007 holds two monitors; the 2024-01-01 unit is the one that ages."""
    result = check_request_eligibility("E-1007", "monitor")

    assert result == Eligibility(
        employee_id="E-1007",
        item="monitor",
        status="eligible",
        reason_code="refresh_elapsed",
        role="director",
        units_on_file=2,
        max_on_file=2,
        oldest_assigned_on="2024-01-01",
        refresh_years=2,
        next_eligible_date="2026-01-01",
    )


def test_laptop_inside_the_refresh_window_is_ineligible() -> None:
    """E-1003's laptop from 2024-08-15 is next eligible on 2028-08-15."""
    result = check_request_eligibility("E-1003", "laptop")

    assert result == Eligibility(
        employee_id="E-1003",
        item="laptop",
        status="ineligible",
        reason_code="refresh_not_elapsed",
        role="individual_contributor",
        units_on_file=1,
        max_on_file=1,
        oldest_assigned_on="2024-08-15",
        refresh_years=4,
        next_eligible_date="2028-08-15",
    )


def test_manager_laptop_inside_the_two_year_window_is_ineligible() -> None:
    """E-1002's laptop from 2025-01-10 is next eligible on 2027-01-10."""
    result = check_request_eligibility("E-1002", "laptop")

    assert result == Eligibility(
        employee_id="E-1002",
        item="laptop",
        status="ineligible",
        reason_code="refresh_not_elapsed",
        role="manager",
        units_on_file=1,
        max_on_file=1,
        oldest_assigned_on="2025-01-10",
        refresh_years=2,
        next_eligible_date="2027-01-10",
    )


def test_headset_inside_the_refresh_window_is_ineligible() -> None:
    """E-1004's headset from 2024-11-01 is next eligible on 2026-11-01."""
    result = check_request_eligibility("E-1004", "headset")

    assert result == Eligibility(
        employee_id="E-1004",
        item="headset",
        status="ineligible",
        reason_code="refresh_not_elapsed",
        role="manager",
        units_on_file=1,
        max_on_file=1,
        oldest_assigned_on="2024-11-01",
        refresh_years=2,
        next_eligible_date="2026-11-01",
    )


def test_monitor_at_the_cap_is_a_replacement_not_an_extra_unit() -> None:
    """Quantity is 1, so a monitor already at the cap is a refresh check."""
    result = check_request_eligibility("E-1001", "monitor")

    assert result.reason_code == "refresh_not_elapsed"
    assert result.next_eligible_date == "2028-06-01"


def test_monitors_at_the_manager_cap_are_a_replacement() -> None:
    """E-1004 already holds two monitors, so a third request checks refresh."""
    result = check_request_eligibility("E-1004", "monitor")

    assert result == Eligibility(
        employee_id="E-1004",
        item="monitor",
        status="ineligible",
        reason_code="refresh_not_elapsed",
        role="manager",
        units_on_file=2,
        max_on_file=2,
        oldest_assigned_on="2025-03-01",
        refresh_years=3,
        next_eligible_date="2028-03-01",
    )


def test_undated_monitor_blocks_a_replacement() -> None:
    """E-1006 is at the monitor cap and the unit on file has no assignment date."""
    result = check_request_eligibility("E-1006", "monitor")

    assert result == Eligibility(
        employee_id="E-1006",
        item="monitor",
        status="undetermined",
        reason_code="incomplete_equipment_record",
        role="individual_contributor",
        units_on_file=1,
        max_on_file=1,
        refresh_years=3,
    )


def test_undated_other_item_does_not_block_a_laptop_refresh() -> None:
    """E-1006's missing monitor date is irrelevant to the laptop replacement."""
    result = check_request_eligibility("E-1006", "laptop")

    assert result.status == "eligible"
    assert result.reason_code == "refresh_elapsed"
    assert result.next_eligible_date == "2025-04-01"


def test_unknown_employee_is_undetermined() -> None:
    """An id absent from the directory stops before policy."""
    result = check_request_eligibility("E-9999", "headset")

    assert result == Eligibility(
        employee_id="E-9999",
        item="headset",
        status="undetermined",
        reason_code="unknown_employee",
    )


def test_contractor_role_has_no_policy() -> None:
    """E-1005 is on file, and contractor has no limits to apply."""
    result = check_request_eligibility("E-1005", "laptop")

    assert result == Eligibility(
        employee_id="E-1005",
        item="laptop",
        status="undetermined",
        reason_code="unknown_role",
        role="contractor",
        units_on_file=1,
        oldest_assigned_on="2025-11-15",
    )


def test_unknown_role_wins_over_an_unlisted_item() -> None:
    """Role is checked before the catalog, so a contractor desk is unknown_role."""
    result = check_request_eligibility("E-1005", "standing_desk")

    assert result.reason_code == "unknown_role"


def test_standing_desk_is_an_unlisted_item() -> None:
    """A concrete item outside the catalog is undetermined for a known role."""
    result = check_request_eligibility("E-1002", "standing_desk")

    assert result == Eligibility(
        employee_id="E-1002",
        item="standing_desk",
        status="undetermined",
        reason_code="unlisted_item",
        role="manager",
        units_on_file=0,
    )
