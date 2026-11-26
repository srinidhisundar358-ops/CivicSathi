from p1_core_backend.mcp_client.hub import McpHub
from shared.ids import DOC_IDS, SERVICE_IDS
from shared.schemas import ActionPlan, ChecklistItem, LifeEvent, UserProfile


async def build_plan(
    hub: McpHub,
    profile: UserProfile,
    event: LifeEvent,
    conversation_id: str,
) -> ActionPlan:
    affected = await hub.call(
        "documents",
        "get_affected_documents",
        {
            "event": event.model_dump(mode="json"),
            "held": [doc.model_dump(mode="json") for doc in profile.documents],
        },
        conversation_id,
    )

    candidates = affected.data if affected.ok and isinstance(affected.data, list) else []
    by_doc = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue

        doc_id = candidate.get("doc_id")
        service_id = candidate.get("service_id")
        if doc_id in DOC_IDS and service_id in SERVICE_IDS:
            by_doc.setdefault(doc_id, candidate)

    if not by_doc:
        return ActionPlan(summary="No relocation checklist is available.", items=[])

    order = await hub.call(
        "documents",
        "get_update_order",
        {"doc_ids": list(by_doc)},
        conversation_id,
    )
    ordered_ids = order.data if order.ok and isinstance(order.data, list) else []
    doc_ids = list(
        dict.fromkeys(
            [doc for doc in ordered_ids if isinstance(doc, str) and doc in by_doc]
            + list(by_doc)
        )
    )

    state = event.to_state or profile.current_state
    items = []

    for doc_id in doc_ids:
        candidate = by_doc[doc_id]
        service_id = candidate["service_id"]
        process = await hub.call(
            "services",
            "get_process",
            {"service_id": service_id, "state": state},
            conversation_id,
        )
        data = process.data if process.ok and isinstance(process.data, dict) else {}
        verified = bool(
            data.get("verified") and process.sources and not process.simulated
        )

        priority = candidate.get("priority")
        reason = candidate.get("reason")
        if affected.simulated or priority not in {"mandatory", "recommended", "depends"}:
            priority = "depends"
            reason = "This document may need review after your move."

        items.append(
            ChecklistItem(
                doc_id=doc_id,
                service_id=service_id,
                action=service_id.replace("_", " ").capitalize(),
                priority=priority,
                reason=reason or "Review this document after your move.",
                steps=data.get("steps") or [],
                required_docs=data.get("required_docs") or [],
                fee=data.get("fee") if verified else None,
                official_link=data.get("official_link"),
                sources=process.sources if verified else [],
            )
        )

    summary = f"Here is your relocation checklist for {state.title()}."
    if any(not item.sources for item in items):
        summary += " Items without sources are unverified."

    return ActionPlan(summary=summary, items=items, reminders_created=[])