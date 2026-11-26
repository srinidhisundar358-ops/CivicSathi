import json
import re
from pathlib import Path
from email.utils import parseaddr


DATA_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "gov_senders.json"
)


def load_senders():
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def is_government(sender: str, channel: str) -> bool:
    config = load_senders()
    sender = sender.strip()

    if channel == "sms":
        sender = sender.upper()

        demo_headers = {"DEMO-DL", "DEMO-PN"}

        if sender in demo_headers:
            return True

        demo_numbers = {
            str(number).strip()
            for number in config.get("demo_numbers", [])
        }

        if sender in demo_numbers:
            return True

        header = re.sub(r"^[A-Z]{2}-", "", sender)
        header = re.sub(r"-(G|S|T|P)$", "", header)

        allowed_headers = {
            value.upper()
            for value in config.get("sms_headers", [])
        }

        return header in allowed_headers

    if channel == "email":
        address = parseaddr(sender)[1].lower()

        if address.count("@") != 1:
            return False

        domain = address.rsplit("@", 1)[1]

        for allowed in config.get("email_domains", []):
            allowed = allowed.lower().lstrip(".")

            if domain == allowed:
                return True

            if domain.endswith("." + allowed):
                return True

        return False

    return False
