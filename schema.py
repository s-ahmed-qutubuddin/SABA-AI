from __future__ import annotations

from database import get_connection


def ensure_runtime_schema() -> None:
    """Apply small backward-compatible migrations to an existing assistant_db."""
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='family_profiles' AND column_name='member_user_id'"
        )
        if int(cur.fetchone()[0]) == 0:
            cur.execute("ALTER TABLE family_profiles ADD COLUMN member_user_id INT NULL")
            cur.execute("ALTER TABLE family_profiles ADD CONSTRAINT fk_family_profiles_member_user FOREIGN KEY (member_user_id) REFERENCES users(user_id) ON DELETE SET NULL")
            cur.execute("CREATE INDEX idx_family_profiles_member_user ON family_profiles(member_user_id)")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS smartthings_tokens (
                token_id TINYINT PRIMARY KEY,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                expires_at DOUBLE NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()
