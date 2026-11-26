from datetime import date, timedelta

from p1_core_backend.db.store import _connection
from shared.schemas import Reminder


def _ensure_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            user_id TEXT NOT NULL,
            doc_id TEXT NOT NULL,
            due_date TEXT NOT NULL,
            payload TEXT NOT NULL,
            PRIMARY KEY (user_id, doc_id, due_date)
        )
        """
    )


def add(reminder: Reminder) -> Reminder:
    key = (
        reminder.user_id,
        reminder.doc_id or "",
        reminder.due_date.isoformat(),
    )
    with _connection() as conn:
        _ensure_table(conn)
        conn.execute(
            """
            INSERT INTO reminders (user_id, doc_id, due_date, payload)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, doc_id, due_date) DO NOTHING
            """,
            (*key, reminder.model_dump_json()),
        )
        row = conn.execute(
            """
            SELECT payload FROM reminders
            WHERE user_id = ? AND doc_id = ? AND due_date = ?
            """,
            key,
        ).fetchone()

    return Reminder.model_validate_json(row[0])


def upcoming(user_id: str, days: int) -> list[Reminder]:
    today = date.today()
    cutoff = today + timedelta(days=days)
    with _connection() as conn:
        _ensure_table(conn)
        rows = conn.execute(
            """
            SELECT payload FROM reminders
            WHERE user_id = ? AND due_date BETWEEN ? AND ?
            ORDER BY due_date, doc_id
            """,
            (user_id, today.isoformat(), cutoff.isoformat()),
        ).fetchall()
    return [Reminder.model_validate_json(payload) for (payload,) in rows]


def overdue(user_id: str) -> list[Reminder]:
    with _connection() as conn:
        _ensure_table(conn)
        rows = conn.execute(
            """
            SELECT payload FROM reminders
            WHERE user_id = ? AND due_date < ?
            ORDER BY due_date, doc_id
            """,
            (user_id, date.today().isoformat()),
        ).fetchall()
    return [Reminder.model_validate_json(payload) for (payload,) in rows]