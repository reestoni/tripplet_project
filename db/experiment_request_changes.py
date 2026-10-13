from __future__ import annotations

# db/experiment_request_changes.py
"""Review-vor-Uebernahme-Workflow fuer tblExperimentRequests.

Ein bereits gespeicherter Request (ChangeOfRequestID IS NULL) darf von
Nicht-Superusern nicht mehr direkt ueberschrieben werden - jede Aenderung
erzeugt/aktualisiert stattdessen eine Kopie-Zeile (ChangeOfRequestID =
Original-ID, RequestStatus = 1 "Request"), die ein Superuser explizit
akzeptieren oder ablehnen muss. Das Original bleibt bis zur Freigabe komplett
unveraendert - inkl. seines aktuellen RequestStatus und einer evtl. bereits
verknuepften tblExperimente-Zeile (die lebt in einer anderen Tabelle und wird
hier nie angefasst).

Genau EINE offene Kopie pro Original: ein erneutes Speichern aktualisiert die
bereits bestehende Kopie statt eine zweite anzulegen (verhindert einen sich
aufstauenden Kopien-Stapel).

Versioning (2026-09-01, user request: an accepted change used to overwrite
the original in place, with no way to trace what it looked like before). Now
the current state is archived BEFORE every overwrite of a LIVE row (both when
accepting a pending change and on a direct superuser edit, see
screen_create_experiment_request.py) as an additional, archived row
(PriorVersionOfID = ID of the LIVE row it is a prior version of) - same
table, same "copy row" pattern as ChangeOfRequestID, just pointing backward
in time (history instead of proposal). Archived rows are pure read-only
snapshots (never themselves editable/acceptable) and therefore need to be
filtered out of every "active requests" listing, just like ChangeOfRequestID
copies (WHERE PriorVersionOfID IS NULL) - see list_versions()/
supports_versioning() and the call sites in main.py, ui/screen_my_requests.py,
ui/screen_create_experiment.py and ui/widgets/sidebar_nav.py (badge counts).
"""

import datetime
from typing import Any, Dict, List, Optional

from db.connection import get_connection, get_columns_map

# Spalten, die beim Uebernehmen einer Kopie ins Original NICHT geschrieben
# werden - sie gehoeren dem Original (Status/Experiment-Zuordnung leben ueber
# RequestStatus + die separate tblExperimente-Verknuepfung) bzw. sind reine
# Kopie-Metadaten ohne Bedeutung fuer das Original. DenialReason gehoert hier
# dazu (Moderations-Feld, wird nur ueber den Status-Wechsel "Denied" in
# screen_my_requests.py gesetzt, nie ueber das normale Bearbeitungsformular -
# eine Kopie hat es daher nie sinnvoll gesetzt und wuerde sonst beim Merge
# einen bestehenden Denial-Grund des Originals grundlos loeschen).
_NON_MERGE_COLS = {
    "ID", "Timestamp", "CreatedBy", "RequestStatus", "ChangeOfRequestID", "DenialReason",
}


def supports_change_tracking() -> bool:
    """True, wenn die aktuell verbundene Umgebung (aktiver TRIPPLET_MODE)
    bereits die ChangeOfRequestID-Spalte hat.

    Stand 2026-09-02: auf dev_local und prod ausgerollt (dev ausstehend) -
    ohne diesen Check crasht jeder Aufruf dort mit "Unknown column
    'ChangeOfRequestID'". Ergebnis ist prozessweit gecacht (ueber
    db.connection.get_columns_map()) - ein bereits laufender Prozess sieht
    einen NACH seinem Start per ALTER TABLE nachgereichten Spalten-Rollout
    daher nie, erst nach einem Neustart.
    """
    try:
        return "changeofrequestid" in get_columns_map("tblExperimentRequests")
    except Exception:
        return False


def supports_versioning() -> bool:
    """True if the currently connected environment already has the
    PriorVersionOfID column (versioning feature, same rollout state as
    supports_change_tracking() - see there for the process-wide-cache
    caveat: rolled out to dev_local and prod as of 2026-09-02, dev
    pending)."""
    try:
        return "priorversionofid" in get_columns_map("tblExperimentRequests")
    except Exception:
        return False


def list_versions(request_id: Any) -> List[Dict[str, Any]]:
    """Returns all archived prior versions of a LIVE row, newest first.
    Each entry: {"ID", "Timestamp", "CreatedByUser"}.

    Empty list if the environment doesn't have PriorVersionOfID yet, or if
    no change was ever accepted for this request."""
    if request_id in (None, "") or not supports_versioning():
        return []
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            "SELECT er.[ID], er.[Timestamp], u.[Username] "
            "FROM [tblExperimentRequests] er "
            "LEFT JOIN [tblUser] u ON u.[ID] = er.[CreatedBy] "
            "WHERE er.[PriorVersionOfID] = ? "
            "ORDER BY er.[Timestamp] DESC",
            [request_id],
        )
        rows = cur.fetchall()
    return [{"ID": r[0], "Timestamp": r[1], "CreatedByUser": r[2]} for r in rows]


def has_versions(request_id: Any) -> bool:
    """True if at least one archived prior version exists for request_id."""
    if request_id in (None, "") or not supports_versioning():
        return False
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            "SELECT 1 FROM [tblExperimentRequests] WHERE [PriorVersionOfID]=? LIMIT 1",
            [request_id],
        )
        return cur.fetchone() is not None


def _archive_current_version_on(cur, request_id: Any) -> Optional[Any]:
    """Core logic of archive_current_version(): saves the current state of
    request_id as a new archived row (PriorVersionOfID=request_id).

    Operates on an ALREADY OPEN cursor (part of a transaction managed by the
    caller) - does NOT commit itself. See archive_current_version() for the
    standalone, committing variant for callers outside their own
    transaction."""
    cur.execute("SELECT * FROM [tblExperimentRequests] WHERE [ID]=?", [request_id])
    row = cur.fetchone()
    if not row:
        return None
    col_names = [d[0] for d in (cur.description or [])]
    values = {col_names[i]: row[i] for i in range(len(col_names))}

    # ID: new identity of its own (autonumber). The LIVE row's own
    # PriorVersionOfID/ChangeOfRequestID are NOT copied 1:1 - PriorVersionOfID
    # is set explicitly to request_id below (links the archive row back to
    # the LIVE row it is a prior version of), ChangeOfRequestID stays NULL
    # (an archive row is never itself an open pending change). Every other
    # column - including RequestStatus/CreatedBy/DenialReason - is
    # deliberately carried over 1:1: the archive is meant to be a faithful
    # snapshot, not a filtered merge result (unlike _NON_MERGE_COLS above,
    # which serves a completely different purpose).
    #
    # Timestamp is the ONE exception: it's part of _NON_MERGE_COLS and stays
    # constant on the LIVE row for its whole lifetime (original creation
    # date, see accept_pending_change()) - a 1:1 copied value would be
    # identical on EVERY archived version and would make list_versions()'
    # "newest first" ordering meaningless. Instead the archive row gets the
    # moment of THIS archiving (= when this version was superseded by the
    # next one) - that keeps versions chronologically distinguishable and is
    # arguably the more useful piece of information for a history anyway
    # ("valid until").
    archive_cols = [c for c in col_names if c not in ("ID", "PriorVersionOfID", "ChangeOfRequestID", "Timestamp")]
    insert_cols = archive_cols + ["PriorVersionOfID", "Timestamp"]
    insert_vals = [values[c] for c in archive_cols] + [request_id, datetime.datetime.now()]
    placeholders = ",".join(["?"] * len(insert_cols))
    col_sql = ",".join([f"[{c}]" for c in insert_cols])
    cur.execute(
        f"INSERT INTO [tblExperimentRequests] ({col_sql}) VALUES ({placeholders})",
        insert_vals,
    )
    new_id = getattr(cur, "lastrowid", None)
    if new_id in (None, 0, ""):
        try:
            cur.execute("SELECT LAST_INSERT_ID()")
            r = cur.fetchone()
            if r and r[0] not in (None, 0, ""):
                new_id = r[0]
        except Exception:
            pass
    return new_id


def archive_current_version(request_id: Any) -> Optional[Any]:
    """Standalone, committing variant of _archive_current_version_on() for
    callers outside their own transaction - currently: a superuser directly
    editing a LIVE row in screen_create_experiment_request.py (best-effort,
    see the call site there - a failure here must not block the actual
    save).

    No-op (returns None) if the environment doesn't have PriorVersionOfID
    yet. Otherwise returns the ID of the new archive row."""
    if request_id in (None, "") or not supports_versioning():
        return None
    with get_connection() as cn:
        cur = cn.cursor()
        new_id = _archive_current_version_on(cur, request_id)
        try:
            cn.commit()
        except Exception:
            pass
    return new_id


def get_pending_change_id(original_id: Any) -> Optional[Any]:
    """Liefert die ID der offenen Aenderungs-Kopie zu original_id, falls vorhanden."""
    if original_id in (None, "") or not supports_change_tracking():
        return None
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            "SELECT [ID] FROM [tblExperimentRequests] WHERE [ChangeOfRequestID]=?",
            [original_id],
        )
        row = cur.fetchone()
    return row[0] if row else None


def get_pending_change_ids(original_ids: List[Any]) -> Dict[Any, Any]:
    """Batch-Variante von get_pending_change_id() fuer eine Liste von Original-IDs.

    Gibt {OriginalID: KopieID} nur fuer Originale mit tatsaechlich offener
    Kopie zurueck (fehlende Eintraege bedeuten: keine offene Kopie).
    """
    ids = [i for i in original_ids if i not in (None, "")]
    if not ids or not supports_change_tracking():
        return {}
    out: Dict[Any, Any] = {}
    chunk_size = 200
    with get_connection() as cn:
        cur = cn.cursor()
        for i in range(0, len(ids), chunk_size):
            chunk = ids[i:i + chunk_size]
            placeholders = ",".join(["?"] * len(chunk))
            cur.execute(
                f"SELECT [ChangeOfRequestID], [ID] FROM [tblExperimentRequests] "
                f"WHERE [ChangeOfRequestID] IN ({placeholders})",
                list(chunk),
            )
            for orig_id, copy_id in cur.fetchall() or []:
                out[orig_id] = copy_id
    return out


def get_change_of(request_id: Any) -> Optional[Any]:
    """Falls request_id selbst eine Aenderungs-Kopie ist: liefert die Original-ID.

    Gibt None zurueck, wenn request_id ein Original ist (oder nicht existiert).
    """
    if request_id in (None, "") or not supports_change_tracking():
        return None
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            "SELECT [ChangeOfRequestID] FROM [tblExperimentRequests] WHERE [ID]=?",
            [request_id],
        )
        row = cur.fetchone()
    if not row or row[0] in (None, ""):
        return None
    return row[0]


def create_or_update_pending_change(
    *, original_id: Any, values: Dict[str, Any], created_by: Any
) -> Any:
    """Legt eine neue Aenderungs-Kopie an oder aktualisiert die bereits offene.

    `values` sind ausschliesslich die Formularfelder (kein ID/Timestamp/
    CreatedBy/RequestStatus/ChangeOfRequestID). Gibt die ID der Kopie zurueck.
    """
    if not supports_change_tracking():
        raise RuntimeError(
            "Diese Umgebung hat die ChangeOfRequestID-Spalte noch nicht "
            "(Aenderungs-Review-Feature ist bisher nur auf dev_local und prod ausgerollt, "
            "nicht auf dev)."
        )
    existing_id = get_pending_change_id(original_id)
    cols = list(values.keys())

    with get_connection() as cn:
        cur = cn.cursor()

        if existing_id is not None:
            if cols:
                set_clause = ",".join([f"[{c}]=?" for c in cols])
                params = [values[c] for c in cols] + [existing_id]
                cur.execute(
                    f"UPDATE [tblExperimentRequests] SET {set_clause} WHERE [ID]=?",
                    params,
                )
            try:
                cn.commit()
            except Exception:
                pass
            return existing_id

        insert_cols = cols + ["Timestamp", "CreatedBy", "RequestStatus", "ChangeOfRequestID"]
        insert_vals = [values[c] for c in cols] + [
            datetime.datetime.now(),
            created_by,
            1,
            original_id,
        ]
        placeholders = ",".join(["?"] * len(insert_cols))
        col_sql = ",".join([f"[{c}]" for c in insert_cols])
        cur.execute(
            f"INSERT INTO [tblExperimentRequests] ({col_sql}) VALUES ({placeholders})",
            insert_vals,
        )
        try:
            cn.commit()
        except Exception:
            pass

        new_id = getattr(cur, "lastrowid", None)
        if new_id in (None, 0, ""):
            try:
                cur.execute("SELECT LAST_INSERT_ID()")
                row = cur.fetchone()
                if row and row[0] not in (None, 0, ""):
                    new_id = row[0]
            except Exception:
                pass
        return new_id


def accept_pending_change(copy_id: Any) -> tuple[Optional[Any], Optional[Any]]:
    """Uebernimmt die Feldwerte der Kopie ins Original, loescht danach die Kopie.

    RequestStatus und alles ausserhalb dieser Tabelle (insb. eine bestehende
    tblExperimente-Verknuepfung) werden beim Original nicht angefasst - ein
    Original, an dem bereits ein Experiment haengt (RequestStatus=4), bleibt
    dadurch automatisch auf Status "Experiment" stehen.

    Archives the original's current state BEFORE overwriting it, as an
    archived prior version (see _archive_current_version_on()/
    list_versions()) - part of the same transaction, so a failure never
    leaves it half-archived or half-merged.

    Returns (original_id, archived_version_id) - the latter is the ID of the
    just-created "before" snapshot (None if this environment doesn't support
    versioning yet, see supports_versioning()). 2026-09-02, user request:
    an already-linked Experiment's owner should be notified that the request
    behind it changed, with a direct link to the old-vs-new diff - the sole
    caller (ExperimentRequestDiffDialog._on_accept()) needs this ID to build
    that link (see ui/notifications.py::create_experiment_request_notification()'s
    PayloadArchivedVersionID). Both None if the copy wasn't found or wasn't
    actually a pending change.
    """
    with get_connection() as cn:
        cn.autocommit = False
        cur = cn.cursor()
        try:
            cur.execute("SELECT * FROM [tblExperimentRequests] WHERE [ID]=?", [copy_id])
            row = cur.fetchone()
            if not row:
                return None, None
            col_names = [d[0] for d in (cur.description or [])]
            values = {col_names[i]: row[i] for i in range(len(col_names))}

            original_id = values.get("ChangeOfRequestID")
            if original_id in (None, ""):
                return None, None

            archived_version_id = None
            if supports_versioning():
                archived_version_id = _archive_current_version_on(cur, original_id)

            set_cols = [c for c in col_names if c not in _NON_MERGE_COLS]
            if set_cols:
                set_clause = ",".join([f"[{c}]=?" for c in set_cols])
                params = [values[c] for c in set_cols] + [original_id]
                cur.execute(
                    f"UPDATE [tblExperimentRequests] SET {set_clause} WHERE [ID]=?",
                    params,
                )

            cur.execute("DELETE FROM [tblExperimentRequests] WHERE [ID]=?", [copy_id])
            cn.commit()
        except Exception:
            try:
                cn.rollback()
            except Exception:
                pass
            raise

    return original_id, archived_version_id


def count_pending_changes(owner_id: Optional[Any] = None) -> int:
    """Zaehlt offene Aenderungs-Kopien.

    `owner_id=None` (Superuser-Sicht): alle offenen Kopien, egal von wem -
    fuer den Review-Badge auf "My Requests". `owner_id=<id>`: nur Kopien
    dieses Nutzers (CreatedBy der Kopie-Zeile) - fuer "meine Aenderung wartet
    noch auf Pruefung"-Sichtbarkeit beim Antragsteller selbst.
    """
    if not supports_change_tracking():
        return 0
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            if owner_id in (None, ""):
                cur.execute(
                    "SELECT COUNT(*) FROM [tblExperimentRequests] WHERE [ChangeOfRequestID] IS NOT NULL"
                )
            else:
                cur.execute(
                    "SELECT COUNT(*) FROM [tblExperimentRequests] "
                    "WHERE [ChangeOfRequestID] IS NOT NULL AND [CreatedBy]=?",
                    [owner_id],
                )
            row = cur.fetchone()
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0


def reject_pending_change(copy_id: Any) -> None:
    """Verwirft eine Aenderungs-Kopie ohne das Original anzufassen."""
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute("DELETE FROM [tblExperimentRequests] WHERE [ID]=?", [copy_id])
        try:
            cn.commit()
        except Exception:
            pass
