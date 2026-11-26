import os
from typing import TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

Model = TypeVar("Model", bound=BaseModel)


class LlmUnavailable(RuntimeError):
    pass


def _request(messages: list[dict], **kwargs) -> dict:
    load_dotenv()
    key = os.getenv("LLM_API_KEY")
    if os.getenv("LLM_MODE", "mock") == "mock" or not key:
        raise LlmUnavailable("LLM is in mock mode or has no API key")
    from openai import OpenAI, OpenAIError

    try:
        with OpenAI(
            base_url=os.getenv("LLM_BASE_URL") or None,
            api_key=key,
            timeout=30.0,
            max_retries=1,
        ) as client:
            response = client.chat.completions.create(
                model=os.getenv("LLM_MODEL") or "",
                messages=messages,
                **kwargs,
            )
        return response.choices[0].message.model_dump(exclude_none=True)
    except OpenAIError as exc:
        raise LlmUnavailable("LLM request failed") from exc


def chat_with_tools(messages: list[dict], tools: list[dict]) -> dict:
    try:
        return _request(messages, **({"tools": tools} if tools else {}))
    except LlmUnavailable:
        return {"role": "assistant", "content": "(mock)"}


def complete_json(prompt: str, schema: type[Model]) -> Model:
    message = _request(
        [
            {"role": "system", "content": f"Return JSON matching this schema: {schema.model_json_schema()}"},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    return schema.model_validate_json(message.get("content") or "")
