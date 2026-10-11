"""The agent fills its tool list from the running MCP server."""

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from equipment_request.agent import ROOT, listed_tools
from equipment_request.react import build_prompt, guard_request


def test_prompt_uses_the_server_catalog() -> None:
    """list_tools supplies the names and schemas the model sees."""

    async def load() -> str:
        """Connect, list tools, and render them into the ReAct prompt."""
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
            tools = listed_tools(listed.tools)
            return build_prompt(guard_request("E-1001", "A laptop."), [], tools)

    prompt = asyncio.run(load())

    assert '<tool name="get_employee_info">' in prompt
    assert '<tool name="get_policy_limits">' in prompt
    assert '<tool name="check_request_eligibility">' in prompt
    assert '<tool name="flag_for_human_review">' in prompt
    assert '"employee_id"' in prompt
    assert "finish is not a server tool" in prompt
