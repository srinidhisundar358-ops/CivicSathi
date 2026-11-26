import asyncio
import json
from pathlib import Path
import sys

import httpx
from mcp import ClientSession
try:  # newer mcp SDKs
    from mcp.client.streamable_http import streamable_http_client
    NEW_SDK = True
except ImportError:  # older mcp SDKs
    from mcp.client.streamable_http import streamablehttp_client as streamable_http_client
    NEW_SDK = False

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import ports
from shared.ids import MCP_SERVERS
from shared.schemas import ToolResult


async def ping(name: str) -> bool:
    try:
        async with asyncio.timeout(5):
            url = ports.mcp_url(getattr(ports, name.upper()))
            async with httpx.AsyncClient(trust_env=False) as client:
                transport = (streamable_http_client(url, http_client=client) if NEW_SDK
                             else streamable_http_client(url))
                async with transport as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool("ping")
        payload = result.structuredContent
        if payload is None:
            payload = json.loads(result.content[0].text)
        envelope = ToolResult.model_validate(payload)
        if result.isError or not envelope.ok or envelope.data != "pong":
            raise ValueError(f"Unexpected ping result: {envelope}")
    except Exception as exc:
        print(f"{name}: FAIL ({exc})")
        return False
    print(f"{name}: OK")
    return True


async def main() -> int:
    return 0 if all(await asyncio.gather(*(ping(name) for name in MCP_SERVERS))) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
