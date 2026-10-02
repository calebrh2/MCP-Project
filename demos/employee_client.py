"""MCP client that calls get_employee_info on the one-tool server.

    uv run python demos/employee_client.py
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main() -> None:
    """Connect over stdio, call get_employee_info, and print the response."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "equipment_request.server"],
        cwd=ROOT,
    )
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        listed = await session.list_tools()
        print("tools:", [tool.name for tool in listed.tools])
        result = await session.call_tool(
            "get_employee_info",
            {"employee_id": "E-1001"},
        )
        if result.is_error:
            raise SystemExit(result)
        print(json.dumps(result.structured_content, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
