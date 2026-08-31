# db/user_directory.py
"""Shared UserID -> display-name lookup.

Used wherever a "who did this" column (e.g. CreatedBy on tblYarn/tblDTYJets)
needs to show a readable name instead of a raw tblUser.ID.
"""

from typing import Dict

from db.connection import fetch_all


def load_user_id_to_name() -> Dict[object, str]:
    """Returns {UserID: "FirstName LastName"} for every tblUser row.

    Keys are stored both as the raw ID and as its string form, so lookups
    work regardless of whether the caller's ID is an int or a str.
    """
    rows = fetch_all(
        "SELECT ID, CONCAT(FirstName, ' ', LastName) AS DisplayName FROM tbluser",
        [],
    )
    out: Dict[object, str] = {}
    for r in rows:
        uid = r.get("ID")
        if uid is None:
            continue
        name = r.get("DisplayName") or f"User {uid}"
        out[uid] = name
        out[str(uid)] = name
    return out
