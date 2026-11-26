from mcp.server.fastmcp import FastMCP

from shared.ports import DIGILOCKER
from shared.schemas import ToolResult

mcp = FastMCP("digilocker", host="0.0.0.0", port=DIGILOCKER)


@mcp.tool()
def ping() -> dict:
    return ToolResult(ok=True, data="pong").model_dump(mode="json")


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
