from __future__ import annotations

from database import get_connection


def _run_write(sql, params=()):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid, cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def _fetch(sql, params=()):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def create_conversation(user_id, title="Saba Session"):
    row_id, _ = _run_write(
        "INSERT INTO conversations (user_id, title) VALUES (%s, %s)",
        (user_id, title),
    )
    return row_id


def conversation_belongs_to_user(conversation_id, user_id):
    rows = _fetch(
        "SELECT conversation_id FROM conversations WHERE conversation_id=%s AND user_id=%s LIMIT 1",
        (conversation_id, user_id),
    )
    return bool(rows)


def get_latest_conversation(user_id):
    rows = _fetch(
        """
        SELECT conversation_id, title, created_at, updated_at
        FROM conversations
        WHERE user_id = %s
        ORDER BY updated_at DESC, conversation_id DESC
        LIMIT 1
        """,
        (user_id,),
    )
    return rows[0] if rows else None


def save_message(conversation_id, message, role):
    if role not in {"user", "assistant", "system"}:
        raise ValueError("Invalid message role")
    row_id, _ = _run_write(
        "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
        (conversation_id, role, message),
    )
    return row_id


def memories(user_id, memory, category="general", importance=5):
    if not memory.strip():
        raise ValueError("Memory cannot be empty")
    importance = max(1, min(10, int(importance)))
    row_id, _ = _run_write(
        "INSERT INTO memories (user_id, memory, category, importance) VALUES (%s, %s, %s, %s)",
        (user_id, memory.strip(), category.strip() or "general", importance),
    )
    return row_id


def notes(user_id, title, content):
    if not title.strip():
        raise ValueError("Note title cannot be empty")
    row_id, _ = _run_write(
        "INSERT INTO notes (user_id, title, content) VALUES (%s, %s, %s)",
        (user_id, title.strip(), content.strip()),
    )
    return row_id


def tasks(user_id, title, description=None, due_date=None):
    if not title.strip():
        raise ValueError("Task title cannot be empty")
    row_id, _ = _run_write(
        "INSERT INTO tasks (user_id, title, description, due_date) VALUES (%s, %s, %s, %s)",
        (user_id, title.strip(), description.strip() if description else None, due_date),
    )
    return row_id


def preferences(user_id, preference_key, preference_value):
    if not preference_key.strip():
        raise ValueError("Preference key cannot be empty")
    _run_write(
        """
        INSERT INTO preferences (user_id, preference_key, preference_value)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE preference_value = VALUES(preference_value)
        """,
        (user_id, preference_key.strip(), preference_value.strip()),
    )


def get_conversations(user_id):
    return _fetch(
        """
        SELECT conversation_id, title, created_at, updated_at
        FROM conversations
        WHERE user_id = %s
        ORDER BY updated_at DESC, conversation_id DESC
        """,
        (user_id,),
    )


def get_messages(user_id, conversation_id):
    return _fetch(
        """
        SELECT m.message_id, m.role, m.content, m.created_at
        FROM messages m
        INNER JOIN conversations c ON c.conversation_id = m.conversation_id
        WHERE m.conversation_id = %s AND c.user_id = %s
        ORDER BY m.created_at ASC, m.message_id ASC
        """,
        (conversation_id, user_id),
    )


def get_recent_messages(conversation_id, limit=12):
    limit = max(1, min(50, int(limit)))
    rows = _fetch(
        f"""
        SELECT role, content
        FROM messages
        WHERE conversation_id = %s
        ORDER BY created_at DESC, message_id DESC
        LIMIT {limit}
        """,
        (conversation_id,),
    )
    return list(reversed(rows))


def get_memories(user_id, limit=12):
    limit = max(1, min(50, int(limit)))
    return _fetch(
        f"""
        SELECT memory_id, memory, category, importance, created_at, updated_at
        FROM memories
        WHERE user_id = %s
        ORDER BY importance DESC, updated_at DESC
        LIMIT {limit}
        """,
        (user_id,),
    )


def _tokenize(text: str) -> set[str]:
    import re
    return {t for t in re.findall(r"[a-zA-Z0-9_]+", (text or '').lower()) if len(t) >= 3}


def search_memories(user_id, query, limit=8):
    """Relevance-aware retrieval using exact phrase, token overlap, category, importance and recency.

    It deliberately avoids an embedding dependency so memory works offline and remains fast
    on the user's local MySQL instance.
    """
    import math
    from datetime import datetime

    limit = max(1, min(20, int(limit)))
    q = (query or "").strip().lower()
    qtokens = _tokenize(q)
    rows = _fetch(
        """
        SELECT memory_id, memory, category, importance, created_at, updated_at
        FROM memories
        WHERE user_id = %s
        ORDER BY updated_at DESC, memory_id DESC
        LIMIT 500
        """,
        (user_id,),
    )
    if not qtokens:
        return rows[:limit]

    scored = []
    now = datetime.now()
    for row in rows:
        text = str(row.get("memory") or "")
        category = str(row.get("category") or "")
        combined = f"{text} {category}".lower()
        mtokens = _tokenize(combined)
        overlap = len(qtokens & mtokens)
        coverage = overlap / max(1, len(qtokens))
        exact_bonus = 8 if q in text.lower() else 0
        category_bonus = 2 if q in category.lower() else 0
        importance_bonus = min(3, int(row.get("importance") or 0) / 4)
        recency_bonus = 0.0
        stamp = row.get("updated_at") or row.get("created_at")
        try:
            days = max(0.0, (now - stamp).total_seconds() / 86400.0)
            recency_bonus = 2.0 * math.exp(-days / 45.0)
        except Exception:
            pass
        score = overlap * 3.0 + coverage * 4.0 + exact_bonus + category_bonus + importance_bonus + recency_bonus
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda pair: (-pair[0], pair[1].get("updated_at") or pair[1].get("created_at")))
    return [row for _, row in scored[:limit]]


def get_notes(user_id):
    return _fetch("SELECT note_id, title, content, created_at, updated_at FROM notes WHERE user_id=%s ORDER BY updated_at DESC, note_id DESC", (user_id,))


def get_tasks(user_id):
    return _fetch(
        """
        SELECT task_id, title, description, status, due_date, created_at, completed_at
        FROM tasks
        WHERE user_id = %s
        ORDER BY CASE WHEN status='pending' THEN 0 ELSE 1 END, due_date IS NULL, due_date ASC, created_at DESC
        """,
        (user_id,),
    )


def get_preferences(user_id):
    return _fetch("SELECT preference_id, preference_key, preference_value, created_at, updated_at FROM preferences WHERE user_id=%s ORDER BY preference_key", (user_id,))


def update_note(user_id, note_id, title, content):
    _, count = _run_write("UPDATE notes SET title=%s, content=%s WHERE note_id=%s AND user_id=%s", (title, content, note_id, user_id))
    return count


def delete_note(user_id, note_id):
    _, count = _run_write("DELETE FROM notes WHERE note_id=%s AND user_id=%s", (note_id, user_id))
    return count


def update_task(user_id, task_id, title, description, due_date, status):
    if status not in {"pending", "completed"}:
        raise ValueError("Invalid task status")
    _, count = _run_write(
        """
        UPDATE tasks SET title=%s, description=%s, due_date=%s, status=%s,
        completed_at=CASE WHEN %s='completed' THEN COALESCE(completed_at, CURRENT_TIMESTAMP) ELSE NULL END
        WHERE task_id=%s AND user_id=%s
        """,
        (title, description, due_date, status, status, task_id, user_id),
    )
    return count


def complete_task(user_id, task_id):
    _, count = _run_write("UPDATE tasks SET status='completed', completed_at=CURRENT_TIMESTAMP WHERE task_id=%s AND user_id=%s", (task_id, user_id))
    return count


def delete_task(user_id, task_id):
    _, count = _run_write("DELETE FROM tasks WHERE task_id=%s AND user_id=%s", (task_id, user_id))
    return count


def delete_memory(user_id, memory_id):
    _, count = _run_write("DELETE FROM memories WHERE memory_id=%s AND user_id=%s", (memory_id, user_id))
    return count
