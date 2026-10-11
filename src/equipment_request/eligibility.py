"""Policy eligibility for a single catalog item.

Quantity is always 1. Free-text exception and wording checks stay with the agent.
Dates are compared to 2026-09-30.
"""

from datetime import date

from equipment_request.employees import get_employee_info
from equipment_request.models.eligibility import Eligibility
from equipment_request.models.policy_limits import CATALOG_ITEMS
from equipment_request.policies import get_policy_limits

_AS_OF = date(2026, 9, 30)


def _add_years(assigned_on: str, years: int) -> str:
    """Calendar anniversary of an assignment date, years ahead."""
    start = date.fromisoformat(assigned_on)
    return start.replace(year=start.year + years).isoformat()


def _oldest_complete(assigned_on: list[str]) -> str | None:
    """Oldest date when every held unit has one, otherwise none."""
    dated = [value for value in assigned_on if value]
    if not dated or len(dated) != len(assigned_on):
        return None
    return min(dated)


def check_request_eligibility(employee_id: str, item: str) -> Eligibility:
    """Return whether this employee may receive one unit of item under policy.

    Stops at the first matching rule: unknown employee, unknown role, unlisted
    item, a replacement blocked by a missing assignment date, issuance under the
    cap, or a refresh that has or has not elapsed.
    """
    info = get_employee_info(employee_id)
    if not info.found or info.role is None:
        return Eligibility(
            employee_id=employee_id,
            item=item,
            status="undetermined",
            reason_code="unknown_employee",
        )

    held = [unit.assigned_on for unit in info.equipment if unit.item == item]
    policy = get_policy_limits(info.role)
    if not policy.found:
        return Eligibility(
            employee_id=employee_id,
            item=item,
            status="undetermined",
            reason_code="unknown_role",
            role=info.role,
            units_on_file=len(held),
            oldest_assigned_on=_oldest_complete(held),
        )

    if item not in CATALOG_ITEMS:
        return Eligibility(
            employee_id=employee_id,
            item=item,
            status="undetermined",
            reason_code="unlisted_item",
            role=info.role,
            units_on_file=len(held),
        )

    row = next(limit for limit in policy.limits if limit.item == item)
    if len(held) < row.max_on_file:
        return Eligibility(
            employee_id=employee_id,
            item=item,
            status="eligible",
            reason_code="issuance_under_max",
            role=info.role,
            units_on_file=len(held),
            max_on_file=row.max_on_file,
            oldest_assigned_on=_oldest_complete(held),
            refresh_years=row.refresh_years,
        )

    if _oldest_complete(held) is None:
        return Eligibility(
            employee_id=employee_id,
            item=item,
            status="undetermined",
            reason_code="incomplete_equipment_record",
            role=info.role,
            units_on_file=len(held),
            max_on_file=row.max_on_file,
            refresh_years=row.refresh_years,
        )

    oldest = min(held)
    next_eligible = _add_years(oldest, row.refresh_years)
    elapsed = date.fromisoformat(next_eligible) <= _AS_OF
    return Eligibility(
        employee_id=employee_id,
        item=item,
        status="eligible" if elapsed else "ineligible",
        reason_code="refresh_elapsed" if elapsed else "refresh_not_elapsed",
        role=info.role,
        units_on_file=len(held),
        max_on_file=row.max_on_file,
        oldest_assigned_on=oldest,
        refresh_years=row.refresh_years,
        next_eligible_date=next_eligible,
    )
