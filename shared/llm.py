import os
from typing import TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

Model = TypeVar("Model", bound=BaseModel)


class LlmUnavailable(RuntimeError):
    """Raised whenever the LLM cannot be used. Callers fall back to rule-based logic."""


def is_mock() -> bool:
    """True when no network call will be made (LLM_MODE=mock or no key)."""
    load_dotenv()
    return os.getenv("LLM_MODE", "mock") == "mock" or not os.getenv("LLM_API_KEY")


def _request(messages: list[dict], **kwargs) -> dict:
    if is_mock():
        raise LlmUnavailable("LLM is in mock mode or has no API key")
    model = os.getenv("LLM_MODEL")
    if not model:
        raise LlmUnavailable("LLM_MODEL is not set")
    from openai import OpenAI, OpenAIError

    try:
        with OpenAI(
            base_url=os.getenv("LLM_BASE_URL") or None,
            api_key=os.getenv("LLM_API_KEY"),
            timeout=30.0,
            max_retries=1,
        ) as client:
            response = client.chat.completions.create(model=model, messages=messages, **kwargs)
        return response.choices[0].message.model_dump(exclude_none=True)
    except (OpenAIError, IndexError, AttributeError) as exc:
        raise LlmUnavailable(f"LLM request failed: {type(exc).__name__}") from exc


def chat_with_tools(messages: list[dict], tools: list[dict]) -> dict:
    """Return the assistant message (OpenAI format, may contain tool_calls).

    Mock mode / no key: returns a plain "(mock)" message and never touches the network.
    Live mode failure (bad key, rate limit, timeout): raises LlmUnavailable so the caller
    can run its scripted fallback instead of showing "(mock)" to the user.
    Blocking call: from async code use `await asyncio.to_thread(chat_with_tools, ...)`.
    """
    if is_mock():
        return {"role": "assistant", "content": "(mock)"}
    return _request(messages, **({"tools": tools} if tools else {}))


def complete_json(prompt: str, schema: type[Model]) -> Model:
    """Return a validated `schema` instance. Raises LlmUnavailable on ANY failure,
    including unparseable or invalid JSON, so callers need only one except clause."""
    message = _request(
        [
            {"role": "system", "content": f"Return JSON matching this schema: {schema.model_json_schema()}"},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    try:
        return schema.model_validate_json(message.get("content") or "")
    except ValidationError as exc:
        raise LlmUnavailable("LLM returned invalid JSON") from exc
