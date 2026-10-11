"""Score agent traces against the four policy examples."""

import json
from pathlib import Path
from typing import Literal

import pytest
from pydantic import BaseModel, model_validator

_GOLDEN_PATH = Path(__file__).parent / "golden" / "equipment_requests.json"
GoldenDecision = Literal["approve", "deny", "escalate"]
GoldenReason = Literal[
    "refresh_not_elapsed",
    "exceeds_role_maximum",
    "unlisted_item",
    "exception_language",
    "vague_item",
    "multiple_items",
    "unknown_employee",
    "unknown_role",
    "incomplete_equipment_record",
]


class GoldenRequest(BaseModel):
    """One equipment request and the decision policy requires."""

    id: str
    employee_id: str
    request: str
    decision: GoldenDecision
    reason: GoldenReason | None = None
    next_eligible_date: str | None = None

    @model_validator(mode="after")
    def reason_matches_decision(self) -> "GoldenRequest":
        """Approve carries no reason. Deny and escalate name one code."""
        if self.decision == "approve":
            if self.reason is not None:
                raise ValueError("approve has no reason code")
        elif self.reason is None:
            raise ValueError("deny and escalate require a reason code")
        if self.reason == "refresh_not_elapsed" and self.next_eligible_date is None:
            raise ValueError("a refresh denial needs next_eligible_date")
        return self


def load_golden(path: Path = _GOLDEN_PATH) -> list[GoldenRequest]:
    """Read the golden request file."""
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise TypeError("golden file must be a list")
    return [GoldenRequest.model_validate(item) for item in payload]


def score_trace(trace: str, case: GoldenRequest) -> list[str]:
    """Return the ways this trace misses the golden decision. Empty means it matches."""
    problems: list[str] = []
    header = f"request: {case.employee_id}: {case.request}"
    if header not in trace:
        problems.append(f"missing header {header}")
    decision = _line_value(trace, "decision")
    if decision != case.decision:
        problems.append(f"decision is {decision or 'missing'}")
    if case.decision == "approve":
        if '"status": "eligible"' not in trace:
            problems.append("missing eligible observation")
    elif case.decision == "deny":
        if f'"reason_code": "{case.reason}"' not in trace:
            problems.append(f"missing reason_code {case.reason}")
        response = _line_value(trace, "response") or ""
        if case.next_eligible_date and case.next_eligible_date not in response:
            problems.append("response missing next eligible date")
    elif case.reason is not None and not _reason_recorded(trace, case.reason):
        problems.append(f"reason {case.reason} was not recorded")
    return problems


def _line_value(trace: str, field: str) -> str | None:
    """Return the final trace field, ignoring draft_decision and draft_response."""
    prefix = f"{field}: "
    value: str | None = None
    for line in trace.splitlines():
        if line.startswith(prefix):
            value = line.removeprefix(prefix)
    return value


def _reason_recorded(trace: str, reason: str) -> bool:
    """True when a flag, a finish, or the final response records this reason code."""
    needle = f'"reason": "{reason}"'
    response = _line_value(trace, "response") or ""
    if reason in response:
        return True
    return any(
        needle in line and line.startswith(("Action: flag_for_human_review", "Action: finish"))
        for line in trace.splitlines()
    )


def _trace(
    case: GoldenRequest,
    *,
    decision: str | None = None,
    observation: str = "",
    action: str = "",
    response: str = "",
) -> str:
    """Build the trace lines the scorer reads."""
    chosen = decision if decision is not None else case.decision
    lines = [
        f"request: {case.employee_id}: {case.request}",
        "",
        "step 1",
        "Thought: Check the request.",
        f"Action: {action}",
        f"Observation: {observation}",
        "",
        f"decision: {chosen}",
        f"response: {response}",
    ]
    return "\n".join(lines)


def test_golden_file_holds_the_four_policy_examples() -> None:
    """The dataset is one approval, one denial, and two different escalations."""
    cases = {case.id: case for case in load_golden()}

    assert set(cases) == {
        "approve_laptop_refresh",
        "deny_laptop_refresh",
        "escalate_unlisted_item",
        "escalate_exception_language",
    }
    assert cases["approve_laptop_refresh"].decision == "approve"
    assert cases["approve_laptop_refresh"].employee_id == "E-1001"
    assert cases["deny_laptop_refresh"].reason == "refresh_not_elapsed"
    assert cases["deny_laptop_refresh"].next_eligible_date == "2028-08-15"
    assert cases["escalate_unlisted_item"].reason == "unlisted_item"
    assert cases["escalate_exception_language"].reason == "exception_language"


@pytest.mark.parametrize(
    ("case_id", "observation", "action", "response"),
    [
        (
            "approve_laptop_refresh",
            '{"status": "eligible", "reason_code": "refresh_elapsed"}',
            'check_request_eligibility {"employee_id": "E-1001", "item": "laptop"}',
            "Approved. The laptop refresh has elapsed.",
        ),
        (
            "deny_laptop_refresh",
            '{"status": "ineligible", "reason_code": "refresh_not_elapsed"}',
            'check_request_eligibility {"employee_id": "E-1003", "item": "laptop"}',
            "Denied. The next eligible date is 2028-08-15.",
        ),
        (
            "escalate_unlisted_item",
            '{"review_id": "R-0001", "reason": "unlisted_item"}',
            'flag_for_human_review {"employee_id": "E-1002", "request": "A standing desk.", "reason": "unlisted_item"}',
            "Escalated for human review. Reason: unlisted_item.",
        ),
        (
            "escalate_exception_language",
            '{"status": "ineligible", "reason_code": "refresh_not_elapsed"}',
            'finish {"decision": "escalate", "reason": "exception_language", "response": "Escalated."}',
            "Escalated for human review. The laptop request cites a coffee spill.",
        ),
    ],
)
def test_matching_trace_scores_clean(
    case_id: str, observation: str, action: str, response: str
) -> None:
    """A trace with the golden decision and recorded evidence has no mismatches."""
    case = next(item for item in load_golden() if item.id == case_id)
    trace = _trace(case, observation=observation, action=action, response=response)

    assert score_trace(trace, case) == []


def test_step_limit_does_not_match_the_approval() -> None:
    """An eligible laptop that never finishes is not the golden approval."""
    case = next(item for item in load_golden() if item.id == "approve_laptop_refresh")
    trace = _trace(
        case,
        decision="escalate",
        observation='{"status": "eligible", "reason_code": "refresh_elapsed"}',
        action='check_request_eligibility {"employee_id": "E-1001", "item": "laptop"}',
        response="Escalated for human review. The agent did not finish within 8 steps.",
    )

    assert "decision is escalate" in score_trace(trace, case)


def test_coffee_spill_denial_does_not_match_the_escalation() -> None:
    """Denying a spill after an ineligible refresh is not exception_language."""
    case = next(
        item for item in load_golden() if item.id == "escalate_exception_language"
    )
    trace = _trace(
        case,
        decision="deny",
        observation='{"status": "ineligible", "reason_code": "refresh_not_elapsed"}',
        action='finish {"decision": "deny", "response": "Denied. The next eligible date is 2028-08-15."}',
        response="Denied. The next eligible date is 2028-08-15.",
    )

    problems = score_trace(trace, case)
    assert "decision is deny" in problems
    assert "reason exception_language was not recorded" in problems
