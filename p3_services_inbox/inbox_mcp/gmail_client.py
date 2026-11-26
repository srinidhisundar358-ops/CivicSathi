import json
from pathlib import Path

from shared.schemas import IncomingMessage


SAMPLE_FILE = (
    Path(__file__).resolve().parent.parent
    / "tests"
    / "sample_messages.json"
)


def consent_url(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "simulated": True
    }


def exchange_code(user_id: str, code: str) -> dict:
    return {
        "user_id": user_id,
        "connected": True,
        "simulated": True
    }


def fetch(
    user_id: str,
    since_hours: int = 24
) -> list[IncomingMessage]:

    with SAMPLE_FILE.open("r", encoding="utf-8") as file:
        samples = json.load(file)

    messages = []

    for sample in samples:
        message = IncomingMessage.model_validate(
            sample["message"]
        )

        if (
            message.user_id == user_id
            and message.channel == "email"
        ):
            messages.append(message)

    return messages
