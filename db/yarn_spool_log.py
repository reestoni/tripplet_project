# db/yarn_spool_log.py
"""Aenderungsprotokoll pro Garnspule (tblYarnSpoolLog), Nutzerwunsch
2026-10-13: "wer hat wann Gewicht/Platz/Status von was auf was geaendert".

Kein volles Buchungsjournal - der Bestand wird weiterhin aus
tblYarnSpool.WeightKg/Status gelesen, das Log ist reine Historie (Anzeige
ueber "History…" in Yarn Stock, spaeter z.B. Verbrauchsauswertungen).

Best-effort wie db/usage_log.py: fehlt die Tabelle (z.B. Prod vor dem
Rollout, Offline-Modus), wird still nichts geschrieben - Yarn Stock
funktioniert unveraendert weiter.

Tabelle anlegen (bewusst manuell, wie tblUsageLog - siehe CREATE_TABLE_SQL):
dev_local per create_table(); dev/prod nur nach ausdruecklicher Freigabe.
Bewusst KEIN Foreign Key auf tblYarnSpool: das Log soll unabhaengig von
der Spulenzeile bestehen bleiben und keine Loeschungen blockieren.
"""
from typing import Any, Dict, Iterable, List, Optional

LOG_TABLE = "tblYarnSpoolLog"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tblYarnSpoolLog (
  ID int NOT NULL AUTO_INCREMENT,
  SpoolID int NOT NULL,
  Action varchar(20) NOT NULL,
  FieldName varchar(30) DEFAULT NULL,
  OldValue varchar(255) DEFAULT NULL,
  NewValue varchar(255) DEFAULT NULL,
  UserID int DEFAULT NULL,
  Username varchar(100) DEFAULT NULL,
  ChangedAt datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (ID),
  KEY idx_spool (SpoolID),
  KEY idx_changedat (ChangedAt)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

# Action-Werte
CREATED, UPDATED, DISCARDED = "created", "updated", "discarded"


def create_table() -> None:
    """Legt tblYarnSpoolLog an (idempotent). Nur bewusst aufrufen."""
    from db.connection import execute
    execute(CREATE_TABLE_SQL)


def fmt_value(value: Any) -> Optional[str]:
    """Einheitliche Textdarstellung fuer Old/NewValue (Zahlen ohne
    Float-Rauschen, None bleibt NULL)."""
    if value is None or value == "":
        return None
    if isinstance(value, float):
        return f"{value:.2f}"
    try:
        from decimal import Decimal
        if isinstance(value, Decimal):
            return f"{float(value):.2f}"
    except Exception:
        pass
    return str(value)[:255]


def log_spool_changes(entries: Iterable[Dict[str, Any]]) -> int:
    """Schreibt Protokollzeilen. Jeder Eintrag: SpoolID, Action, optional
    Field, Old, New. Schlaegt nie sichtbar fehl; gibt die Anzahl geschriebener
    Zeilen zurueck."""
    entries = list(entries)
    if not entries:
        return 0
    try:
        import app_meta
        from db.connection import execute, table_exists
        if not table_exists(LOG_TABLE):
            return 0
        user = getattr(app_meta, "current_user", {}) or {}
        user_id, username = user.get("id"), user.get("username")
        n = 0
        for e in entries:
            try:
                execute(
                    f"INSERT INTO {LOG_TABLE} "
                    "([SpoolID],[Action],[FieldName],[OldValue],[NewValue],[UserID],[Username]) "
                    "VALUES (?,?,?,?,?,?,?)",
                    [int(e["SpoolID"]), e["Action"], e.get("Field"),
                     fmt_value(e.get("Old")), fmt_value(e.get("New")), user_id, username],
                )
                n += 1
            except Exception as ex:
                print(f"[YarnSpoolLog] insert failed for spool {e.get('SpoolID')}: {ex}")
        return n
    except Exception as ex:
        print(f"[YarnSpoolLog] logging skipped: {ex}")
        return 0


def fetch_spool_history(spool_ids: List[int]) -> List[Dict[str, Any]]:
    """Protokoll der angegebenen Spulen, neueste zuerst. Leere Liste, wenn
    die Tabelle fehlt."""
    if not spool_ids:
        return []
    from db.connection import fetch_all, table_exists
    if not table_exists(LOG_TABLE):
        return []
    ph = ",".join(["?"] * len(spool_ids))
    rows = fetch_all(
        f"SELECT [ID], [SpoolID], [Action], [FieldName], [OldValue], [NewValue], "
        f"[Username], [ChangedAt] FROM {LOG_TABLE} WHERE [SpoolID] IN ({ph}) "
        f"ORDER BY [ChangedAt] DESC, [ID] DESC",
        [int(i) for i in spool_ids],
    )
    # Schluessel vereinheitlichen: die SQL-Uebersetzung liefert z.B. "UserName"
    # statt "Username" zurueck (auf dev_local beobachtet).
    canon = {k.lower(): k for k in ("ID", "SpoolID", "Action", "FieldName", "OldValue",
                                    "NewValue", "Username", "ChangedAt")}
    return [{canon.get(k.lower(), k): v for k, v in r.items()} for r in rows]


def log_table_exists() -> bool:
    try:
        from db.connection import table_exists
        return bool(table_exists(LOG_TABLE))
    except Exception:
        return False
