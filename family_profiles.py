from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from database import get_connection
from config import ROOT, SABA_USER_ID

PROFILE_FILE = Path(ROOT) / "family_profiles.json"


def _owner_profile_row(cur):
    cur.execute(
        "SELECT * FROM family_profiles WHERE relationship_to_owner='self' ORDER BY profile_id LIMIT 1"
    )
    return cur.fetchone()


def ensure_user_for_profile(cur, profile: dict[str, Any], owner_user_id: int | None = None) -> int:
    preferred = (profile.get("preferred_name") or "").strip()
    label = (profile.get("label") or "").strip()
    if profile.get("relationship_to_owner") == "self" and owner_user_id:
        return int(owner_user_id)
    name = label or preferred
    cur.execute("SELECT user_id FROM users WHERE LOWER(name)=LOWER(%s) LIMIT 1", (name,))
    row = cur.fetchone()
    if row:
        return int(row["user_id"])
    cur.execute("INSERT INTO users (name) VALUES (%s)", (name,))
    return int(cur.lastrowid)


def seed_family_profiles(path: str | Path = PROFILE_FILE) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Family profile seed file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = payload.get("profiles") or []
    if not profiles:
        raise ValueError("No family profiles found in seed file")

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # Ensure the canonical owner user exists first.
        owner_profile = next((p for p in profiles if p.get("relationship_to_owner") == "self"), profiles[0])
        owner_name = owner_profile.get("label") or "SABA Owner"
        cur.execute("SELECT user_id FROM users WHERE LOWER(name)=LOWER(%s) LIMIT 1", (owner_name,))
        row = cur.fetchone()
        if row:
            owner_user_id = int(row["user_id"])
        else:
            cur.execute("INSERT INTO users (name) VALUES (%s)", (owner_name,))
            owner_user_id = int(cur.lastrowid)

        seeded = []
        for profile in profiles:
            label = str(profile.get("label") or "").strip()
            relationship = str(profile.get("relationship_to_owner") or "").strip()
            if not label or not relationship:
                continue
            cur.execute(
                "SELECT profile_id, member_user_id FROM family_profiles WHERE owner_user_id=%s AND label=%s LIMIT 1",
                (owner_user_id, label),
            )
            existing = cur.fetchone()
            if existing:
                profile_id = int(existing["profile_id"])
                member_user_id = existing.get("member_user_id")
            else:
                cur.execute(
                    """
                    INSERT INTO family_profiles
                    (owner_user_id,label,relationship_to_owner,preferred_name,languages,role_title,occupation,interests,notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        owner_user_id,
                        label,
                        relationship,
                        profile.get("preferred_name"),
                        profile.get("languages"),
                        profile.get("role_title"),
                        profile.get("occupation"),
                        profile.get("interests"),
                        profile.get("notes"),
                    ),
                )
                profile_id = int(cur.lastrowid)
                member_user_id = None
            if relationship == "self":
                member_user_id = owner_user_id
            elif not member_user_id:
                member_user_id = ensure_user_for_profile(cur, profile, owner_user_id)
            cur.execute(
                """
                UPDATE family_profiles
                SET relationship_to_owner=%s, preferred_name=%s, languages=%s,
                    role_title=%s, occupation=%s, interests=%s, notes=%s, member_user_id=%s
                WHERE profile_id=%s AND owner_user_id=%s
                """,
                (
                    relationship,
                    profile.get("preferred_name"),
                    profile.get("languages"),
                    profile.get("role_title"),
                    profile.get("occupation"),
                    profile.get("interests"),
                    profile.get("notes"),
                    member_user_id,
                    profile_id,
                    owner_user_id,
                ),
            )
            seeded.append({"profile_id": profile_id, "user_id": int(member_user_id), "label": label, "role": "owner" if relationship == "self" else "family_member"})

        conn.commit()
        return {"owner_user_id": owner_user_id, "profiles_seeded": len(seeded), "profiles": seeded}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def get_owner_user_id() -> int:
    conn = get_connection(); cur = conn.cursor(dictionary=True)
    try:
        row = _owner_profile_row(cur)
        if row and row.get("owner_user_id"):
            return int(row["owner_user_id"])
        return SABA_USER_ID
    finally:
        cur.close(); conn.close()


def list_profiles(user_id: int = SABA_USER_ID) -> list[dict[str, Any]]:
    owner_user_id = user_id
    conn = get_connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT fp.profile_id, fp.owner_user_id, fp.label, fp.relationship_to_owner,
                   fp.preferred_name, fp.languages, fp.role_title, fp.occupation,
                   fp.interests, fp.notes, fp.member_user_id,
                   u.name AS member_user_name,
                   fp.created_at, fp.updated_at
            FROM family_profiles fp
            LEFT JOIN users u ON u.user_id = fp.member_user_id
            WHERE fp.owner_user_id = %s
            ORDER BY CASE WHEN fp.relationship_to_owner='self' THEN 0 ELSE 1 END, fp.profile_id
            """,
            (owner_user_id,),
        )
        return cur.fetchall()
    finally:
        cur.close(); conn.close()


def get_profile_by_id(profile_id: int, owner_user_id: int) -> dict[str, Any] | None:
    rows = [r for r in list_profiles(owner_user_id) if int(r["profile_id"]) == int(profile_id)]
    return rows[0] if rows else None


def ensure_member_user_for_profile(profile_id: int, owner_user_id: int) -> int:
    conn = get_connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM family_profiles WHERE profile_id=%s AND owner_user_id=%s LIMIT 1", (profile_id, owner_user_id))
        profile = cur.fetchone()
        if not profile:
            raise ValueError("Family profile not found")
        if profile.get("member_user_id"):
            return int(profile["member_user_id"])
        if profile.get("relationship_to_owner") == "self":
            member_user_id = owner_user_id
        else:
            member_user_id = ensure_user_for_profile(cur, profile, owner_user_id)
        cur.execute("UPDATE family_profiles SET member_user_id=%s WHERE profile_id=%s AND owner_user_id=%s", (member_user_id, profile_id, owner_user_id))
        conn.commit()
        return int(member_user_id)
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()


def upsert_profile(label: str, relationship_to_owner: str, preferred_name: str | None = None, languages: str | None = None,
                   role_title: str | None = None, occupation: str | None = None, interests: str | None = None,
                   notes: str | None = None, user_id: int = SABA_USER_ID) -> int:
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT profile_id FROM family_profiles WHERE owner_user_id=%s AND label=%s LIMIT 1", (user_id, label))
        row = cur.fetchone()
        if row:
            profile_id = int(row[0])
            cur.execute(
                "UPDATE family_profiles SET relationship_to_owner=%s, preferred_name=%s, languages=%s, role_title=%s, occupation=%s, interests=%s, notes=%s WHERE profile_id=%s AND owner_user_id=%s",
                (relationship_to_owner, preferred_name, languages, role_title, occupation, interests, notes, profile_id, user_id),
            )
        else:
            cur.execute(
                "INSERT INTO family_profiles (owner_user_id,label,relationship_to_owner,preferred_name,languages,role_title,occupation,interests,notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (user_id, label, relationship_to_owner, preferred_name, languages, role_title, occupation, interests, notes),
            )
            profile_id = int(cur.lastrowid)
        conn.commit()
        return profile_id
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()


def delete_profile(profile_id: int, user_id: int = SABA_USER_ID) -> bool:
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM family_profiles WHERE profile_id=%s AND owner_user_id=%s AND relationship_to_owner<>'self'", (profile_id, user_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        cur.close(); conn.close()


def find_or_create_member_user(name: str, owner_user_id: int = SABA_USER_ID):
    query = name.strip().lower()
    if not query:
        raise ValueError("Family member name is required")
    rows = list_profiles(owner_user_id)
    profile = None
    for row in rows:
        if query in {str(row.get("label") or "").lower(), str(row.get("preferred_name") or "").lower(), str(row.get("relationship_to_owner") or "").lower()}:
            profile = row; break
    if profile is None:
        terms = {t for t in query.split() if len(t) >= 3}
        scored = []
        for row in rows:
            blob = " ".join(str(row.get(k) or "") for k in ("label", "preferred_name", "relationship_to_owner")).lower()
            score = sum(1 for term in terms if term in blob)
            if score: scored.append((score, row))
        if scored:
            profile = sorted(scored, key=lambda p: (-p[0], int(p[1]["profile_id"])))[0][1]
    if not profile:
        raise ValueError(f"No family profile matched '{name}'")
    user_id = ensure_member_user_for_profile(int(profile["profile_id"]), owner_user_id)
    profile["member_user_id"] = user_id
    return profile, user_id


def relevant_context(query: str = "", limit: int = 12, user_id: int = SABA_USER_ID) -> str:
    rows = list_profiles(user_id)
    if not rows:
        return ""
    limit = max(1, min(25, int(limit)))
    terms = {t for t in query.lower().split() if len(t) > 2}
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        blob = " ".join(str(row.get(k) or "") for k in row.keys()).lower()
        score = sum(1 for t in terms if t in blob)
        if not terms and row.get("relationship_to_owner") in {"self", "father", "mother"}:
            score += 3
        scored.append((score, row))
    scored.sort(key=lambda x: (-x[0], int(x[1].get("profile_id") or 0)))
    chosen = [row for _, row in scored[:limit]]
    lines = []
    for row in chosen:
        fields = []
        for key in ("relationship_to_owner", "preferred_name", "languages", "role_title", "occupation", "interests", "notes"):
            if row.get(key):
                fields.append(f"{key}: {row[key]}")
        lines.append(f"- {row.get('label')}: " + "; ".join(fields))
    return "Family profiles:\n" + "\n".join(lines)


def get_profile_for_user(user_id: int, owner_user_id: int) -> dict[str, Any] | None:
    for row in list_profiles(owner_user_id):
        if row.get("member_user_id") and int(row["member_user_id"]) == int(user_id):
            return row
    return None
