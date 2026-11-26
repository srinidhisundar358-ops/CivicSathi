import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    value = value.strip().lower()
    if value in {"true", "1", "yes", "on"}:
        return True
    if value in {"false", "0", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


@dataclass(frozen=True)
class Settings:
    use_stubs: bool
    stub_servers: frozenset[str]
    db_path: Path
    backend_public_url: str
    llm_mode: str
    fallback_to_stub_on_error: bool


settings = Settings(
    use_stubs=env_bool("USE_STUBS", True),
    stub_servers=frozenset(
        name.strip().lower()
        for name in os.getenv("STUB_SERVERS", "").split(",")
        if name.strip()
    ),
    db_path=REPO_ROOT / Path(os.getenv("DB_PATH", "./civicsaathi.db")),
    backend_public_url=os.getenv(
        "BACKEND_PUBLIC_URL", "http://localhost:8000"
    ).rstrip("/"),
    llm_mode=os.getenv("LLM_MODE", "mock").strip().lower(),
    fallback_to_stub_on_error=env_bool("FALLBACK_TO_STUB_ON_ERROR", True),
)