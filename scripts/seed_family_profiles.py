from __future__ import annotations

from family_profiles import seed_family_profiles


if __name__ == "__main__":
    result = seed_family_profiles()
    print(f"Family profiles imported: {result['profiles_seeded']} profiles; owner_user_id={result['owner_user_id']}")
