
import json
import httpx

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from shared.ports import SERVICES, mcp_url


SERVICES_URL = mcp_url(SERVICES)


async def call_service_tool(tool_name, arguments):

    async with httpx.AsyncClient(
        trust_env=False,
        timeout=30
    ) as client:

        async with streamable_http_client(
            SERVICES_URL,
            http_client=client
        ) as (read, write, _):

            async with ClientSession(read, write) as session:

                await session.initialize()

                result = await session.call_tool(
                    tool_name,
                    arguments=arguments
                )

                if result.isError:
                    raise RuntimeError(
                        f"Service Intelligence error: {tool_name}"
                    )

                payload = result.structuredContent

                if payload is None:
                    payload = json.loads(
                        result.content[0].text
                    )

                if isinstance(payload, dict) and "ok" in payload:

                    if not payload["ok"]:
                        raise RuntimeError(
                            payload.get("error", "Service tool failed")
                        )

                    return payload.get("data")

                return payload
