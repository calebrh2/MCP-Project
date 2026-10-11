"""Smallest MCP server: one trivial tool, no business logic.

Start it over stdio (blocks until a client connects):

    uv run mcp run demos/minimal_server.py

Or over HTTP:

    uv run mcp run demos/minimal_server.py --transport streamable-http
"""

from mcp.server import MCPServer

mcp = MCPServer("Demo")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    print("ADDING TWO NUMBERS...")
    return a + b


if __name__ == "__main__":
    mcp.run()
