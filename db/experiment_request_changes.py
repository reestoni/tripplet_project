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

    Stand CLAUDE.md: bisher nur auf dev_local ausgerollt, dev/prod folgen erst
    nach separater Freigabe - ohne diesen Check crasht jeder Aufruf dort mit
    "Unknown column 'ChangeOfRequestID'". Ergebnis ist prozessweit gecacht
    (ueber db.connection.get_columns_map()).
    """
    try:
        return "changeofrequestid" in get_columns_map("tblExperimentRequests")
    except Exception:
        return False


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
            "(Aenderungs-Review-Feature ist bisher nur auf dev_local ausgerollt)."
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


def accept_pending_change(copy_id: Any) -> Optional[Any]:
    """Uebernimmt die Feldwerte der Kopie ins Original, loescht danach die Kopie.

    RequestStatus und alles ausserhalb dieser Tabelle (insb. eine bestehende
    tblExperimente-Verknuepfung) werden beim Original nicht angefasst - ein
    Original, an dem bereits ein Experiment haengt (RequestStatus=4), bleibt
    dadurch automatisch auf Status "Experiment" stehen.

    Gibt die Original-ID zurueck, oder None falls die Kopie nicht gefunden
    wurde oder keine Kopie war.
    """
    with get_connection() as cn:
        cn.autocommit = False
        cur = cn.cursor()
        try:
            cur.execute("SELECT * FROM [tblExperimentRequests] WHERE [ID]=?", [copy_id])
            row = cur.fetchone()
            if not row:
                return None
            col_names = [d[0] for d in (cur.description or [])]
            values = {col_names[i]: row[i] for i in range(len(col_names))}

            original_id = values.get("ChangeOfRequestID")
            if original_id in (None, ""):
                return None

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

    return original_id


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
