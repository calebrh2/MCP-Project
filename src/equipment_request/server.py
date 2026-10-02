"""MCP server that exposes employee directory lookup.

Start it over stdio:

    uv run python -m equipment_request.server
"""

from mcp.server import MCPServer

from equipment_request.employees import get_employee_info

mcp = MCPServer("Equipment Request")
mcp.tool()(get_employee_info)


def main() -> None:
    """Serve get_employee_info over stdio until the client disconnects."""
    mcp.run()


if __name__ == "__main__":
    main()
