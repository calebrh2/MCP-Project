"""Role policy lookup.

Limits are the per-item cap and refresh interval from the requirements table.
"""

import json
from pathlib import Path

from pydantic import BaseModel

from equipment_request.models.policy_limits import PolicyLimit, PolicyLimits

_POLICIES_PATH = Path(__file__).resolve().parent / "data" / "policies.json"


class PolicyRecord(BaseModel):
    """One role in the mock policy table."""

    role: str
    limits: list[PolicyLimit]


def _load_policies() -> dict[str, PolicyRecord]:
    """Read the mock policy table keyed by role."""
    raw: object = json.loads(_POLICIES_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise TypeError("policy table must be a JSON list")
    records = [PolicyRecord.model_validate(row) for row in raw]
    return {record.role: record for record in records}


def get_policy_limits(role: str) -> PolicyLimits:
    """Return the catalog limits for a role.

    A known role returns four rows: item, max_on_file, and refresh_years.
    An unknown role, including contractor, returns found=false and no rows.
    """
    record = _load_policies().get(role)
    if record is None:
        return PolicyLimits(role=role, found=False)
    return PolicyLimits(role=record.role, found=True, limits=record.limits)
