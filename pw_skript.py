#!/usr/bin/env python3
"""
Migrates plaintext passwords from tblUser.pw to tblUser.pw_hash using Argon2.

Default behaviour:
- Only updates rows where pw_hash IS NULL (or empty) AND pw IS NOT NULL/empty
- Does NOT delete plaintext pw unless --wipe-plain is provided

Run:
  python migrate_passwords_to_hash.py

Optional:
  python migrate_passwords_to_hash.py --wipe-plain
  python migrate_passwords_to_hash.py --limit 10
  python migrate_passwords_to_hash.py --user someUser
"""

import argparse
from argon2 import PasswordHasher

# Import your existing DB connection wrapper
from db.connection import get_connection, current_db_name


def is_empty(val) -> bool:
    return val is None or (isinstance(val, str) and val.strip() == "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wipe-plain", action="store_true",
                        help="After hashing, set tblUser.pw = NULL (removes plaintext passwords).")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of users processed (0 = no limit).")
    parser.add_argument("--user", type=str, default="",
                        help="Only migrate a single username (exact match).")
    args = parser.parse_args()

    ph = PasswordHasher()  # sichere Defaults

    print(f"DB: {current_db_name()}")
    print("Selecting users to migrate...")

    # Query: users with plaintext pw, but missing pw_hash
    sql = (
        "SELECT [Username], [pw], [pw_hash] "
        "FROM tblUser "
        "WHERE ([pw] IS NOT NULL) "
        "AND (TRIM([pw]) <> '') "
        "AND ([pw_hash] IS NULL OR TRIM([pw_hash]) = '')"
    )

    params = []
    if args.user.strip():
        sql += " AND [Username]=?"
        params.append(args.user.strip())

    if args.limit and args.limit > 0:
        # MySQL LIMIT (your SQL translator doesn't add it automatically)
        sql += " LIMIT " + str(int(args.limit))

    migrated = 0
    skipped = 0

    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql, tuple(params))
        rows = cur.fetchall() or []

        print(f"Found {len(rows)} user(s) to migrate.")

        for username, pw, pw_hash in rows:
            if is_empty(username) or is_empty(pw):
                skipped += 1
                continue

            # Safety: if pw_hash already exists, skip
            if not is_empty(pw_hash):
                skipped += 1
                continue

            new_hash = ph.hash(str(pw))

            # Update hash
            cur.execute(
                "UPDATE tblUser SET [pw_hash]=? WHERE [Username]=?",
                (new_hash, username),
            )

            if args.wipe_plain:
                cur.execute(
                    "UPDATE tblUser SET [pw]=NULL WHERE [Username]=?",
                    (username,),
                )

            migrated += 1
            print(f"  migrated: {username}")

    print("\nDone.")
    print(f"Migrated: {migrated}")
    print(f"Skipped:  {skipped}")
    if not args.wipe_plain:
        print("\nNOTE: plaintext passwords were NOT removed. "
              "Re-run with --wipe-plain once you have updated TrippleT login code.")


if __name__ == "__main__":
    main()
