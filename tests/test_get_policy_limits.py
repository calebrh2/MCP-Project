"""Unit tests for get_policy_limits, called directly rather than over MCP."""

from equipment_request.models.policy_limits import PolicyLimit, PolicyLimits
from equipment_request.policies import get_policy_limits


def test_individual_contributor_has_four_catalog_rows() -> None:
    """An individual contributor gets one of each item, with the published intervals."""
    limits = get_policy_limits("individual_contributor")

    assert limits == PolicyLimits(
        role="individual_contributor",
        found=True,
        limits=[
            PolicyLimit(item="laptop", max_on_file=1, refresh_years=4),
            PolicyLimit(item="monitor", max_on_file=1, refresh_years=3),
            PolicyLimit(item="docking_station", max_on_file=1, refresh_years=4),
            PolicyLimit(item="headset", max_on_file=1, refresh_years=2),
        ],
    )


def test_manager_laptop_refreshes_every_two_years() -> None:
    """Managers replace a laptop on a two-year interval and may hold two monitors."""
    limits = get_policy_limits("manager")

    assert limits.found is True
    by_item = {row.item: row for row in limits.limits}
    assert by_item["laptop"] == PolicyLimit(
        item="laptop", max_on_file=1, refresh_years=2
    )
    assert by_item["monitor"].max_on_file == 2


def test_director_has_four_catalog_rows() -> None:
    """A director gets one of each item, with the published intervals."""
    limits = get_policy_limits("director")

    assert limits == PolicyLimits(
        role="director",
        found=True,
        limits=[
            PolicyLimit(item="laptop", max_on_file=1, refresh_years=2),
            PolicyLimit(item="monitor", max_on_file=2, refresh_years=2),
            PolicyLimit(item="docking_station", max_on_file=1, refresh_years=2),
            PolicyLimit(item="headset", max_on_file=1, refresh_years=1),
        ],
    )


def test_contractor_has_no_policy_rows() -> None:
    """A role outside the policy table is a not-found result."""
    limits = get_policy_limits("contractor")

    assert limits == PolicyLimits(role="contractor", found=False)


def test_unknown_role_has_no_policy_rows() -> None:
    """A role string that is not on file returns no rows."""
    limits = get_policy_limits("intern")

    assert limits == PolicyLimits(role="intern", found=False)
