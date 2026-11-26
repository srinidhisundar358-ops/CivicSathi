from mcp.server.fastmcp import FastMCP

from shared.ports import SERVICES
from shared.schemas import ToolResult

mcp = FastMCP("services", host="0.0.0.0", port=SERVICES)


@mcp.tool()
def ping() -> dict:
    return ToolResult(ok=True, data="pong").model_dump(mode="json")


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
