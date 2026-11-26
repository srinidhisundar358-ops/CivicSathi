import json
import re
from pathlib import Path
from datetime import date

import pytest

from shared.schemas import IncomingMessage
from p3_services_inbox.inbox_mcp.extractor import extract
from p3_services_inbox.services_mcp.server import get_process


SAMPLE_FILE = Path(__file__).parent / "sample_messages.json"


def load_samples():
    with SAMPLE_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")


def test_category_accuracy():
    samples = load_samples()
    assert len(samples) == 18

    correct = 0

    for sample in samples:
        message = IncomingMessage.model_validate(
            sample["message"]
        )

        result = extract(message)

        if result.category == sample["expected"]["category"]:
            correct += 1

    accuracy = correct / len(samples)

    assert accuracy >= 0.90, (
        f"Category accuracy: {accuracy:.1%}"
    )


def test_otp_protection():
    checked = 0

    for sample in load_samples():
        if sample["expected"]["category"] != "otp":
            continue

        message = IncomingMessage.model_validate(
            sample["message"]
        )

        result = extract(message)

        assert result.category == "otp"
        assert result.summary == "OTP message dropped"
        assert result.confidence == 1.0
        assert result.application_ref is None
        assert result.amount is None

        codes = re.findall(
            r"\b\d{4,8}\b", message.text
        )

        for code in codes:
            assert code not in result.summary

        checked += 1

    assert checked == 3


def test_demo_messages():
    expected = {
        "demo_ravi": (
            "driving_licence",
            "dl_renewal",
            date(2027, 1, 5)
        ),
        "demo_ajji": (
            "pension_ppo",
            "pension_life_certificate",
            date(2026, 11, 30)
        )
    }

    checked = set()

    for sample in load_samples():
        if not sample.get("demo"):
            continue

        message = IncomingMessage.model_validate(
            sample["message"]
        )

        if message.user_id not in expected:
            continue

        doc_id, service_id, due_date = expected[
            message.user_id
        ]

        result = extract(message)

        assert result.category == "deadline"
        assert result.doc_id == doc_id
        assert result.service_id == service_id
        assert result.due_date == due_date

        checked.add(message.user_id)

    assert checked == set(expected)


def test_voter_shift():
    result = get_process(
        "voter_shift", "maharashtra"
    )

    assert result["ok"] is True
    assert result["data"]["verified"] is True
    assert result["data"]["official_link"]
    assert result["data"]["steps"]
    assert result["sources"]

    for source in result["sources"]:
        assert source["url"]
        date.fromisoformat(source["last_verified"])


def test_unknown_service():
    result = get_process(
        "unknown_service", "karnataka"
    )

    assert result["ok"] is True
    assert result["data"]["verified"] is False
    assert result["data"]["steps"] == []
