"""MCP server that exposes equipment-request tools.

Start it over stdio:

    uv run python -m equipment_request.server
"""

from mcp.server import MCPServer

from equipment_request.eligibility import check_request_eligibility
from equipment_request.employees import get_employee_info
from equipment_request.policies import get_policy_limits
from equipment_request.reviews import flag_for_human_review

mcp = MCPServer("Equipment Request")
mcp.tool()(get_employee_info)
mcp.tool()(get_policy_limits)
mcp.tool()(check_request_eligibility)
mcp.tool()(flag_for_human_review)


def main() -> None:
    """Serve equipment-request tools over stdio until the client disconnects."""
    mcp.run()


if __name__ == "__main__":
    main()
