"""MCP client that calls the equipment-request tools.

Run it with:

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
    """Connect over stdio, call each registered tool, and print the responses."""
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
        print("get_employee_info:")
        print(json.dumps(result.structured_content, indent=2))
        result = await session.call_tool(
            "get_policy_limits",
            {"role": "manager"},
        )
        if result.is_error:
            raise SystemExit(result)
        print("get_policy_limits:")
        print(json.dumps(result.structured_content, indent=2))
        result = await session.call_tool(
            "check_request_eligibility",
            {"employee_id": "E-1001", "item": "laptop"},
        )
        if result.is_error:
            raise SystemExit(result)
        print("check_request_eligibility:")
        print(json.dumps(result.structured_content, indent=2))
        result = await session.call_tool(
            "flag_for_human_review",
            {
                "employee_id": "E-1005",
                "request": "A laptop refresh.",
                "reason": "unknown_role",
            },
        )
        if result.is_error:
            raise SystemExit(result)
        print("flag_for_human_review:")
        print(json.dumps(result.structured_content, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
