"""ReAct agent for one equipment request.

Connects to the equipment-request MCP server, then lets the model choose
tools until it finishes or uses eight calls. Run it with:

    uv run python -m equipment_request.agent
    uv run python -m equipment_request.agent E-1001 "Replace the laptop. It is old and slow."
"""

import asyncio
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from equipment_request.ollama import OllamaModel
from equipment_request.react import EmployeeIdError, ListedTool, ReactResult, run_react

ROOT = Path(__file__).resolve().parents[2]
_TRACES_DIR = ROOT / "traces"
DEFAULT_EMPLOYEE_ID = "E-1001"
DEFAULT_REQUEST = "Replace the laptop. It is old and slow."


class AdvertisedTool(Protocol):
    """The fields read from one MCP list_tools entry."""

    name: str
    description: str | None
    input_schema: dict[str, Any]


def listed_tools(tools: Iterable[AdvertisedTool]) -> list[ListedTool]:
    """Copy the server catalog into the types the ReAct loop stores."""
    return [
        ListedTool(
            name=tool.name,
            description=tool.description or "",
            input_schema=tool.input_schema,
        )
        for tool in tools
    ]


async def _call_tool(
    session: ClientSession, name: str, arguments: dict[str, Any]
) -> object:
    """Call one MCP tool and return its structured content, or an error object."""
    result = await session.call_tool(name, arguments)
    if result.is_error or result.structured_content is None:
        return {"error": str(result)}
    return result.structured_content


async def run_agent(employee_id: str, request_text: str) -> ReactResult:
    """Open the MCP server and run the ReAct loop for this request."""
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

        async def call_tool(name: str, arguments: dict[str, Any]) -> object:
            """Forward one validated action to the open session."""
            return await _call_tool(session, name, arguments)

        return await run_react(
            OllamaModel(),
            call_tool,
            tools,
            employee_id,
            request_text,
            _TRACES_DIR,
        )


def main() -> None:
    """Decide the default request, or the employee id and text given as arguments."""
    args = sys.argv[1:]
    if not args:
        employee_id, request_text = DEFAULT_EMPLOYEE_ID, DEFAULT_REQUEST
    elif len(args) == 2:
        employee_id, request_text = args
    else:
        raise SystemExit(
            'usage: python -m equipment_request.agent [EMPLOYEE_ID "request text"]'
        )
    try:
        result = asyncio.run(run_agent(employee_id, request_text))
    except EmployeeIdError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"trace: {result.trace_path}")
    print(f"steps: {len(result.steps)}")
    if result.reflection is not None:
        label = "passes" if result.reflection.passes else "fails"
        print(f"reflection: {label}")
        print(f"reflection_reason: {result.reflection.reason}")
    print(f"decision: {result.decision}")
    print(f"response: {result.response}")
    if result.review_id is not None:
        print(f"review_id: {result.review_id}")


if __name__ == "__main__":
    main()
