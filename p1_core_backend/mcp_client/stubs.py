
import re
from copy import deepcopy

from p1_core_backend.config import REPO_ROOT
from shared.ids import SERVICE_IDS
from shared.schemas import ToolResult


TOOL_HEADING = re.compile(
    r"^###\s+`([a-z_]+__[a-z_]+)`\s*$", re.MULTILINE
)
OUTPUT_BLOCK = re.compile(
    r"^Output[^\n]*\n\s*```json[ \t]*\n(.*?)\n```",
    re.MULTILINE | re.DOTALL,
)


class StubHub:
    def __init__(self):
        path = REPO_ROOT / "shared" / "tool_contracts.md"
        sections = TOOL_HEADING.split(path.read_text(encoding="utf-8"))
        self.examples = {}

        for name, section in zip(sections[1::2], sections[2::2]):
            self.examples[name] = [
                ToolResult.model_validate_json(block).model_dump(mode="json")
                for block in OUTPUT_BLOCK.findall(section)
            ]

    def call(self, server: str, tool: str, args: dict) -> ToolResult:
        name = f"{server}__{tool}"
        examples = self.examples.get(name)
        if not examples:
            return ToolResult(
                ok=False, error=f"No stub example for {name}", simulated=True
            )

        service_id = args.get("service_id")
        unknown_service = (
            service_id is not None and service_id not in SERVICE_IDS
        )

        if unknown_service and name == "services__get_process" and len(examples) > 1:
            result = deepcopy(examples[1])
        elif unknown_service:
            return ToolResult(
                ok=False,
                error="unverified: not in our official data",
                simulated=True,
            )
        else:
            result = deepcopy(examples[0])

        if name in {"services__get_process", "documents__get_required_docs"}:
            data = result["data"]
            if isinstance(data, dict):
                for field in ("service_id", "state"):
                    if field in args:
                        data[field] = args[field]

        # A service fixture describes one specific service and state.
        # Keep the sample guidance only when both match the request.
        if name == "services__get_process":
            fixture = examples[0]["data"]
            matches_fixture = all(
                args.get(field) == fixture.get(field)
                for field in ("service_id", "state")
            )
            result["data"]["verified"] = False
            result["sources"] = []
            if not matches_fixture:
                result["data"].update(
                    authority=None,
                    official_link=None,
                    steps=[],
                    fee=None,
                    required_docs=[],
                    processing_time=None,
                )
                result["error"] = "unverified: not in our official data"

        result["simulated"] = True
        return ToolResult.model_validate(result)