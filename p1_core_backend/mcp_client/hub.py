import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

import httpx
from mcp import ClientSession

try:
    from mcp.client.streamable_http import streamable_http_client
except ImportError:
    from mcp.client.streamable_http import streamablehttp_client
    streamable_http_client = None

from p1_core_backend.config import settings
from p1_core_backend.db import store
from p1_core_backend.mcp_client.stubs import StubHub
from shared import ports
from shared.ids import DOC_IDS, EVENTS, MCP_SERVERS, SERVICE_IDS, STATES
from shared.schemas import ToolResult


logger = logging.getLogger(__name__)

# Keys define which tools the chat agent may call.
# Values define the arguments advertised when using stubs.
LLM_TOOLS = {
    "documents__get_affected_documents": {"event": "object", "held": "array"},
    "documents__get_update_order": {"doc_ids": "array"},
    "documents__get_required_docs": {"service_id": "string", "state": "string"},
    "documents__get_alternatives": {"doc_id": "string", "purpose": "string"},
    "services__get_process": {"service_id": "string", "state": "string"},
    "services__get_authority": {"service_id": "string", "state": "string"},
    "services__explain_term": {"term": "string", "language": "string"},
    "deadlines__list_upcoming": {"user_id": "string", "days": "integer"},
    "deadlines__get_renewal_rule": {"doc_id": "string"},
}


@asynccontextmanager
async def _session(server: str):
    url = ports.mcp_url(getattr(ports, server.upper()))
    async with asyncio.timeout(8):
        if streamable_http_client is not None:
            async with httpx.AsyncClient(trust_env=False) as client:
                async with streamable_http_client(url, http_client=client) as streams:
                    async with ClientSession(*streams[:2]) as session:
                        await session.initialize()
                        yield session
        else:
            async with streamablehttp_client(url) as streams:
                async with ClientSession(*streams[:2]) as session:
                    await session.initialize()
                    yield session


def _function(name: str, schema: dict, description: str = "") -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description or name.replace("__", ": ").replace("_", " "),
            "parameters": schema,
        },
    }


def _trace_args(server: str, tool: str, args: dict) -> dict:
    if server == "inbox" and tool == "extract_from_message":
        message = args.get("message", {})
        if not isinstance(message, dict):
            return {}
        return {
            field: message[field]
            for field in ("message_id", "sender", "channel")
            if isinstance(message.get(field), str)
        }

    allowed_values = {
        "doc_id": DOC_IDS,
        "service_id": SERVICE_IDS,
        "state": [*STATES, "central"],
    }
    safe = {
        field: args[field]
        for field, values in allowed_values.items()
        if args.get(field) in values
    }
    event = args.get("event")
    if isinstance(event, dict):
        safe["event"] = {
            field: event[field]
            for field, values in (
                ("event_type", EVENTS),
                ("from_state", STATES),
                ("to_state", STATES),
            )
            if event.get(field) in values
        }
    doc_ids = args.get("doc_ids")
    if isinstance(doc_ids, list):
        safe["doc_ids"] = [doc_id for doc_id in doc_ids if doc_id in DOC_IDS]
    return safe


class McpHub:
    def __init__(self):
        self.stubs = StubHub()
        self.real_tools = {}
        self.unavailable = set()

    def _uses_stub(self, server: str) -> bool:
        return settings.use_stubs or server in settings.stub_servers

    async def _discover(self, server: str, session: ClientSession):
        tools = {}
        cursor = None

        while True:
            response = await session.list_tools(cursor=cursor)
            for tool in response.tools:
                name = f"{server}__{tool.name}"
                if name in LLM_TOOLS:
                    tools[name] = _function(
                        name, tool.inputSchema, tool.description or ""
                    )
            cursor = response.nextCursor
            if not cursor:
                break

        self.real_tools[server] = tools
        self.unavailable.discard(server)

    async def _check_server(self, server: str):
        try:
            async with _session(server) as session:
                await self._discover(server, session)
        except Exception:
            self.unavailable.add(server)
            logger.info("MCP server unavailable at startup: %s", server)

    async def startup(self):
        await asyncio.gather(
            *(
                self._check_server(server)
                for server in MCP_SERVERS
                if not self._uses_stub(server)
            )
        )

    def llm_tools(self) -> list[dict]:
        functions = []
        for name, fields in LLM_TOOLS.items():
            server, _ = name.split("__", 1)

            if self._uses_stub(server) or (
                server in self.unavailable and settings.fallback_to_stub_on_error
            ):
                properties = {}
                for field, kind in fields.items():
                    schema = {"type": kind}
                    if kind == "array":
                        schema["items"] = {
                            "type": "object" if field == "held" else "string"
                        }
                    properties[field] = schema
                functions.append(
                    _function(
                        name,
                        {
                            "type": "object",
                            "properties": properties,
                            "required": list(fields),
                        },
                    )
                )
            else:
                function = self.real_tools.get(server, {}).get(name)
                if function:
                    functions.append(function)

        return functions

    async def _call_real(self, server: str, tool: str, args: dict) -> ToolResult:
        async with _session(server) as session:
            if server not in self.real_tools or server in self.unavailable:
                await self._discover(server, session)
            response = await session.call_tool(tool, args)

        if response.isError:
            raise ValueError("MCP reported a tool error")

        payload = response.structuredContent
        if payload is None:
            payload = json.loads(response.content[0].text)
        if isinstance(payload, dict) and set(payload) == {"result"}:
            payload = payload["result"]
        return ToolResult.model_validate(payload)

    def _call_stub(self, server: str, tool: str, args: dict) -> ToolResult:
        try:
            return self.stubs.call(server, tool, args)
        except (TypeError, ValueError, KeyError):
            return ToolResult(ok=False, error="Invalid stub result", simulated=True)

    async def call(
        self,
        server: str,
        tool: str,
        args: dict,
        conversation_id: str | None = None,
    ) -> ToolResult:
        started = perf_counter()
        source = "real"

        if server not in MCP_SERVERS:
            result = ToolResult(ok=False, error="Unknown MCP server")
        elif self._uses_stub(server):
            source = "stub"
            result = self._call_stub(server, tool, args)
        else:
            try:
                result = await self._call_real(server, tool, args)
            except Exception:
                self.unavailable.add(server)
                if settings.fallback_to_stub_on_error:
                    source = "fallback"
                    result = self._call_stub(server, tool, args)
                else:
                    result = ToolResult(ok=False, error="MCP call failed")

        # Tool output can contain private data or echo its input.
        trace_result = ToolResult(ok=result.ok, simulated=result.simulated)
        try:
            await asyncio.to_thread(
                store.save_trace,
                uuid4().hex,
                conversation_id,
                server,
                tool,
                _trace_args(server, tool, args),
                trace_result.model_dump(mode="json"),
                datetime.now(timezone.utc).isoformat(),
                (perf_counter() - started) * 1000,
                source,
            )
        except Exception:
            logger.warning("Could not save MCP trace")

        return result