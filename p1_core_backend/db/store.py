import json
import sqlite3
from contextlib import closing, contextmanager

from p1_core_backend.config import REPO_ROOT, settings
from shared.schemas import ExtractedInfo, Notification, PrefilledForm, UserProfile


TABLES = (
    "profiles",
    "conversations",
    "traces",
    "extracted",
    "notifications",
    "forms",
    "devices",
)


@contextmanager
def _connection():
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(
        sqlite3.connect(settings.db_path, timeout=10, check_same_thread=False)
    ) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        with conn:
            yield conn


def _create_tables(conn):
    for table in TABLES:
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {table} "
            "(id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
        )


def _seed_profiles(conn, profiles):
    for profile in profiles:
        conn.execute(
            "INSERT OR IGNORE INTO profiles (id, payload) VALUES (?, ?)",
            (profile.user_id, profile.model_dump_json()),
        )


def _demo_profiles():
    path = REPO_ROOT / "shared" / "samples.json"
    samples = json.loads(path.read_text(encoding="utf-8"))
    return [
        UserProfile.model_validate(samples["profiles"][user_id])
        for user_id in ("demo_ravi", "demo_ajji")
    ]


def seed_demo():
    profiles = _demo_profiles()
    with _connection() as conn:
        _create_tables(conn)
        _seed_profiles(conn, profiles)


def reset_demo():
    profiles = _demo_profiles()
    with _connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        for table in TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table}")

        # The deadlines MCP creates this table when its storage is initialized.
        reminders = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'reminders'"
        ).fetchone()
        if reminders:
            conn.execute("DELETE FROM reminders")

        _create_tables(conn)
        _seed_profiles(conn, profiles)

    for pdf in (REPO_ROOT / "generated").glob("*.pdf"):
        pdf.unlink(missing_ok=True)


def _save(table, record_id, payload):
    with _connection() as conn:
        conn.execute(
            f"INSERT INTO {table} (id, payload) VALUES (?, ?) "
            "ON CONFLICT(id) DO UPDATE SET payload = excluded.payload",
            (record_id, json.dumps(payload)),
        )


def _get(table, record_id):
    with _connection() as conn:
        row = conn.execute(
            f"SELECT payload FROM {table} WHERE id = ?", (record_id,)
        ).fetchone()
    return json.loads(row[0]) if row else None


def _get_model(table, record_id, model):
    payload = _get(table, record_id)
    return model.model_validate(payload) if payload is not None else None


def save_profile(profile: UserProfile):
    _save("profiles", profile.user_id, profile.model_dump(mode="json"))


def get_profile(user_id: str) -> UserProfile | None:
    return _get_model("profiles", user_id, UserProfile)
def list_profiles() -> list[UserProfile]:
    with _connection() as conn:
        rows = conn.execute(
            "SELECT payload FROM profiles ORDER BY id"
        ).fetchall()
    return [UserProfile.model_validate_json(payload) for (payload,) in rows]


def save_conversation(conversation_id: str, user_id: str):
    _save("conversations", conversation_id, {"user_id": user_id})


def get_conversation(conversation_id: str):
    return _get("conversations", conversation_id)


def save_trace(
    trace_id: str,
    conversation_id: str | None,
    server: str,
    tool: str,
    redacted_args: dict,
    result: dict,
    timestamp: str,
    duration_ms: float,
    source: str,
):
    # The hub supplies sanitized arguments and results.
    _save(
        "traces",
        trace_id,
        {
            "conversation_id": conversation_id,
            "server": server,
            "tool": tool,
            "args": redacted_args,
            "result": result,
            "timestamp": timestamp,
            "duration_ms": duration_ms,
            "source": source,
            **({"fallback": "stub"} if source == "fallback" else {}),
        },
    )


def get_trace(trace_id: str):
    return _get("traces", trace_id)
def list_traces(conversation_id: str) -> list[dict]:
    with _connection() as conn:
        rows = conn.execute(
            """
            SELECT payload FROM traces
            WHERE json_extract(payload, '$.conversation_id') = ?
            ORDER BY rowid
            """,
            (conversation_id,),
        ).fetchall()

    return [json.loads(payload) for (payload,) in rows]


def save_extracted(info: ExtractedInfo):
    _save("extracted", info.message_id, info.model_dump(mode="json"))


def get_extracted(message_id: str) -> ExtractedInfo | None:
    return _get_model("extracted", message_id, ExtractedInfo)


def save_notification(notification: Notification):
    _save(
        "notifications",
        notification.notification_id,
        notification.model_dump(mode="json"),
    )


def get_notification(notification_id: str) -> Notification | None:
    return _get_model("notifications", notification_id, Notification)
def list_notifications(user_id: str) -> list[Notification]:
    with _connection() as conn:
        rows = conn.execute(
            """
            SELECT payload FROM notifications
            WHERE json_extract(payload, '$.user_id') = ?
            """,
            (user_id,),
        ).fetchall()

    notices = [Notification.model_validate_json(payload) for (payload,) in rows]
    return sorted(notices, key=lambda notice: notice.created_at.timestamp(), reverse=True)


def save_form(form: PrefilledForm):
    _save("forms", form.form_id, form.model_dump(mode="json"))


def get_form(form_id: str) -> PrefilledForm | None:
    return _get_model("forms", form_id, PrefilledForm)


def save_device(device_id: str, user_id: str, token: str):
    _save("devices", device_id, {"user_id": user_id, "token": token})


def get_device(device_id: str):
    return _get("devices", device_id)