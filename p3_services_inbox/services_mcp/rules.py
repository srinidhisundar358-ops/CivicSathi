import json
from pathlib import Path
from copy import deepcopy


DATA_DIR = Path(__file__).resolve().parent / "data"


def load_data(filename):
    file_path = DATA_DIR / filename

    if not file_path.exists():
        return {}

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def lookup(service_id, state):
    state = (state or "central").strip().lower()

    if state in ("karnataka", "maharashtra"):
        state_data = load_data(f"{state}.json")
        service = state_data.get(service_id)

        if service is not None:
            return prepare_result(service)

    central_data = load_data("central.json")
    service = central_data.get(service_id)

    if service is not None:
        return prepare_result(service)

    return None


def prepare_result(service):
    result = deepcopy(service)

    result["verified"] = bool(
        result.get("sources")
        and result.get("official_link")
    )

    return result
