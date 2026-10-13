from __future__ import annotations
# ui/notifications.py
"""Zentrale Notification-Logik für TrippleT.

Wird aufgerufen wenn eine TrialSeries auf 'Done' gesetzt wird.
Erstellt Notifications für:
  1. Alle ProcessOwner des Prozesses der Maschine dieser Series
  2. Den Ersteller des verknüpften ExperimentRequests (falls vorhanden)

Duplikate (jemand ist ProcessOwner UND Request-Ersteller) → nur eine Notification.

DB-Tabellen (müssen existieren):
  tblNotification   (ID, RecipientUserID, TrialSeriesID, CreatedAt, ReadAt)
  tblProcessOwner   (ID, ProzessID, UserID)
  tblMaschine       (ID, ..., ProzessID)
  tblTrialSeries    (ID, ..., MachineID)
"""

from typing import List, Optional, Any
from db.connection import fetch_all, execute as _execute, table_exists, get_columns_map as _columns_map


def _tables_ready() -> bool:
    """Gibt True zurück wenn die Kern-Notification-Tabelle existiert.
    tblProcessOwner wird nur fuer create_done_notifications() gebraucht
    (dort separat via _get_process_owners abgefragt, mit eigenem Fallback) -
    Lesen/Zaehlen/Anzeigen von Notifications soll davon nicht abhaengen."""
    return table_exists("tblnotification")


def _get_process_owners(series_id: int) -> List[int]:
    """Gibt alle UserIDs der ProcessOwner des Prozesses dieser Series zurück.

    Kette: tblTrialSeries.MachineID
           → tblMaschine.ProzessID
           → tblProcessOwner.UserID
    """
    try:
        rows = fetch_all(
            """
            SELECT po.UserID
            FROM tblTrialSeries ts
            JOIN tblMaschine m ON m.ID = ts.MachineID
            JOIN tblProcessOwner po ON po.ProzessID = m.ProzessID
            WHERE ts.ID = ?
            """,
            [series_id],
        )
        return [int(r["UserID"]) for r in rows if r.get("UserID")]
    except Exception:
        return []


def _get_experiment_request_creator(series_id: int) -> Optional[int]:
    """Gibt die UserID des ExperimentRequest-Erstellers zurück (falls vorhanden)."""
    try:
        rows = fetch_all(
            """
            SELECT er.CreatedBy
            FROM tblTrialSeries ts
            JOIN tblExperimente e ON e.ID = ts.ExperimentID
            JOIN tblExperimentRequests er ON er.ID = e.ExperimentRequestID
            WHERE ts.ID = ?
            LIMIT 1
            """,
            [series_id],
        )
        if rows and rows[0].get("CreatedBy"):
            return int(rows[0]["CreatedBy"])
    except Exception:
        pass
    return None


def create_done_notifications(
    series_id: int,
    sender_user_id: Optional[int] = None,
) -> int:
    """Erstellt Notifications für alle Empfänger wenn eine Series auf 'Done' gesetzt wird.

    Returns:
        Anzahl erstellter Notifications.
    """
    if not _tables_ready():
        return 0

    # Empfänger sammeln (dedupliziert)
    recipients: List[int] = []

    for uid in _get_process_owners(series_id):
        if uid not in recipients:
            recipients.append(uid)

    creator = _get_experiment_request_creator(series_id)
    if creator and creator not in recipients:
        recipients.append(creator)

    if not recipients:
        return 0

    n = 0
    for uid in recipients:
        try:
            _execute(
                """
                INSERT INTO tblNotification
                    (RecipientUserID, TrialSeriesID, CreatedAt, ReadAt)
                VALUES (?, ?, NOW(), NULL)
                """,
                [uid, series_id],
            )
            n += 1
        except Exception as e:
            import traceback
            print(f"[Notification] INSERT fehlgeschlagen für uid={uid}, series={series_id}: {e}")
            traceback.print_exc()

    return n


def get_superuser_ids() -> List[int]:
    """Gibt die UserIDs aller Superuser (AccessLevel >= 4) zurück.

    tbluser.AccessRights ist ein FK auf tblAccessRight.ID - die eigentliche
    Stufe steht in tblAccessRight.AccessLevel, NICHT direkt in tbluser
    (siehe db.connection.get_user_access_level fuer dasselbe Muster)."""
    try:
        rows = fetch_all(
            "SELECT u.ID FROM tbluser u "
            "INNER JOIN tblAccessRight ar ON u.AccessRights = ar.ID "
            "WHERE ar.AccessLevel >= 4"
        )
        return [int(r["ID"]) for r in rows if r.get("ID")]
    except Exception:
        return []


def create_yarn_stock_notifications(warnings: List[dict]) -> int:
    """Erstellt fuer jeden Superuser eine Notification pro Garn (seit
    2026-10-13; vorher pro Garn/Batch - Aufrufer uebergibt dafuer Charge=None)
    mit Status 'Low' oder 'Empty' - aber nur, wenn dafuer noch KEINE Notification
    (gelesen ODER ungelesen) mit derselben Message existiert.

    Bewusst NICHT mehr "nur ungelesene" (frueherer Bug, siehe CLAUDE.md,
    Nutzerbericht "low stock messages bleiben in meiner glocke, auch wenn ich
    sie als gelesen markiere"): reload_data() in screen_yarn_stock.py ruft
    diese Funktion bei JEDEM Öffnen/Reload des Screens auf - solange das
    Garn/Batch weiter unter dem Schwellwert bleibt, erzeugte die alte "nur
    ungelesene"-Pruefung nach dem Lesen sofort beim naechsten Screen-Besuch
    eine inhaltsgleiche NEUE Notification, die Glocke wurde also nie
    tatsaechlich leer. Ein gelesenes "Low stock"/"Empty stock" gilt jetzt als
    endgueltig erledigt fuer genau diesen Zustand - erst wenn das Garn/Batch
    zwischenzeitlich wieder auf 'OK' war (siehe
    expire_recovered_yarn_stock_notifications(), von reload_data() fuer genau
    diesen Zweck zusaetzlich aufgerufen) UND danach erneut unter den
    Schwellwert faellt, kann wieder eine neue Notification mit derselben
    Message entstehen (die alte, "OK"-ueberholte wurde dann bereits geloescht).

    `warnings`: Liste von Dicts mit 'YarnID', 'YarnName', 'Charge', 'Status'.
    YarnID/Charge werden zusaetzlich strukturiert gespeichert (PayloadYarnID/
    PayloadCharge), damit ein Klick auf die Notification spaeter direkt zur
    richtigen Zeile in Yarn Stock springen kann, ohne die Message-Zeile
    fehleranfaellig zurueckparsen zu muessen.
    """
    if not table_exists("tblnotification") or not warnings:
        return 0
    recipients = get_superuser_ids()
    if not recipients:
        return 0

    has_payload_cols = "payloadyarnid" in _columns_map("tblnotification")

    n = 0
    for w in warnings:
        # Seit 2026-10-13 gilt der Status pro Garn (Charge=None -> Meldung ohne
        # Batch). Der Batch-Zweig bleibt nur fuer eventuelle Altaufrufer.
        if w.get("Charge") is None:
            message = f"{w['Status']} stock: {w['YarnName']}"
        else:
            message = f"{w['Status']} stock: {w['YarnName']} (Batch {w.get('Charge') or '–'})"
        yarn_id = w.get("YarnID")
        for uid in recipients:
            try:
                existing = fetch_all(
                    "SELECT ID FROM tblNotification WHERE RecipientUserID = ? "
                    "AND NotificationType = 'yarn_stock' AND Message = ?",
                    [uid, message],
                )
                if existing:
                    continue  # gibt's fuer diesen User/Garn/Batch/Zustand schon (gelesen oder nicht)
                if has_payload_cols:
                    _execute(
                        "INSERT INTO tblNotification "
                        "(RecipientUserID, TrialSeriesID, CreatedAt, ReadAt, Message, "
                        "NotificationType, PayloadYarnID, PayloadCharge) "
                        "VALUES (?, NULL, NOW(), NULL, ?, 'yarn_stock', ?, ?)",
                        [uid, message, yarn_id, w.get("Charge")],
                    )
                else:
                    _execute(
                        "INSERT INTO tblNotification "
                        "(RecipientUserID, TrialSeriesID, CreatedAt, ReadAt, Message, NotificationType) "
                        "VALUES (?, NULL, NOW(), NULL, ?, 'yarn_stock')",
                        [uid, message],
                    )
                n += 1
            except Exception as e:
                print(f"[Notification] Yarn-Stock-Insert fehlgeschlagen fuer uid={uid}: {e}")
    return n


def expire_recovered_yarn_stock_notifications(ok_pairs: List[dict]) -> int:
    """Löscht bestehende yarn_stock-Notifications für Garn/Batch-Kombinationen,
    die inzwischen wieder auf Status 'OK' sind.

    Seit 2026-10-13 nicht mehr aufgerufen (Status pro Garn) - ersetzt durch
    expire_yarn_stock_notifications_for_yarns().

    Gegenstück zu create_yarn_stock_notifications()'s "Message existiert schon
    (gelesen oder nicht) -> nicht nochmal anlegen"-Dedup: ohne dieses Aufräumen
    würde ein Garn/Batch, das sich erholt und danach ERNEUT unter den
    Schwellwert fällt, nie wieder eine neue Notification auslösen - die alte,
    inzwischen inhaltlich überholte Zeile mit identischer Message würde die
    Dedup-Prüfung fälschlich weiter blockieren. Von screen_yarn_stock.py's
    reload_data() direkt neben create_yarn_stock_notifications() aufgerufen.

    `ok_pairs`: Liste von Dicts mit 'YarnID'/'Charge'. Braucht die Payload-
    Spalten (siehe create_yarn_stock_notifications()) um ein Garn/Batch
    eindeutig einer Notification zuzuordnen - no-opt still, falls diese auf
    der jeweiligen Umgebung (noch) fehlen.
    """
    if not ok_pairs or not table_exists("tblnotification"):
        return 0
    if "payloadyarnid" not in _columns_map("tblnotification"):
        return 0
    n = 0
    for pair in ok_pairs:
        yarn_id = pair.get("YarnID")
        if yarn_id is None:
            continue
        charge = pair.get("Charge")
        try:
            n += _execute(
                "DELETE FROM tblNotification WHERE NotificationType = 'yarn_stock' "
                "AND PayloadYarnID = ? "
                "AND (PayloadCharge = ? OR (PayloadCharge IS NULL AND ? IS NULL))",
                [yarn_id, charge, charge],
            ) or 0
        except Exception as e:
            print(f"[Notification] Yarn-Stock-Expire fehlgeschlagen fuer yarn={yarn_id}: {e}")
    return n


def expire_yarn_stock_notifications_for_yarns(yarn_ids: List[int]) -> int:
    """Loescht ALLE yarn_stock-Notifications der angegebenen Garne (egal
    welche Batch) - Gegenstueck zu create_yarn_stock_notifications() fuer den
    Status pro Garn (seit 2026-10-13): Garn wieder 'OK' -> alte Low/Empty-
    Meldungen weg, damit ein erneutes Unterschreiten wieder meldet.
    No-op, falls die Payload-Spalten auf der Umgebung fehlen."""
    if not yarn_ids or not table_exists("tblnotification"):
        return 0
    if "payloadyarnid" not in _columns_map("tblnotification"):
        return 0
    n = 0
    for yarn_id in yarn_ids:
        try:
            n += _execute(
                "DELETE FROM tblNotification WHERE NotificationType = 'yarn_stock' "
                "AND PayloadYarnID = ?",
                [yarn_id],
            ) or 0
        except Exception as e:
            print(f"[Notification] Yarn-Stock-Expire fehlgeschlagen fuer yarn={yarn_id}: {e}")
    return n


def remove_legacy_batch_yarn_stock_notifications() -> int:
    """Entfernt yarn_stock-Notifications aus der Zeit vor 2026-10-13, als der
    Status noch pro Garn/Batch berechnet wurde (erkennbar an gesetzter
    PayloadCharge bzw. "(Batch ...)" in der Message). Sie wuerden sonst neben
    den neuen Meldungen pro Garn stehen bleiben. Idempotent - nach der ersten
    Ausfuehrung findet der DELETE nichts mehr."""
    if not table_exists("tblnotification"):
        return 0
    try:
        if "payloadcharge" in _columns_map("tblnotification"):
            # Beide Merkmale pruefen: es gibt Altmeldungen mit "(Batch ...)" in
            # der Message, aber leerer PayloadCharge (auf dev_local gefunden,
            # vermutlich vor Einfuehrung der Payload-Spalten entstanden).
            return _execute(
                "DELETE FROM tblNotification WHERE NotificationType = 'yarn_stock' "
                "AND (PayloadCharge IS NOT NULL OR Message LIKE '%(Batch %')"
            ) or 0
        return _execute(
            "DELETE FROM tblNotification WHERE NotificationType = 'yarn_stock' "
            "AND Message LIKE '%(Batch %'"
        ) or 0
    except Exception as e:
        print(f"[Notification] Legacy-Yarn-Stock-Cleanup fehlgeschlagen: {e}")
        return 0


def create_experiment_request_notification(recipient_user_id: Any, request_id: Any, message: str) -> bool:
    """Legt eine 'experiment_request'-Notification an (Statuswechsel eines
    Requests, oder Aenderungskopie akzeptiert/abgelehnt - siehe
    ui/screen_my_requests.py). Klick navigiert ueber PayloadExperimentRequestID
    zu 'My Requests'.

    Payload-Spalte existiert bisher nur auf Umgebungen mit dem
    Aenderungs-Review-Feature (dev_local/prod, siehe
    db/experiment_request_changes.py) - fehlt sie, wird die Notification ohne
    Payload angelegt (Klick geht dann einfach nicht zur richtigen Zeile,
    kein Fehler).
    """
    if not _tables_ready() or recipient_user_id in (None, ""):
        return False
    has_payload_col = "payloadexperimentrequestid" in _columns_map("tblnotification")
    try:
        if has_payload_col:
            _execute(
                "INSERT INTO tblNotification "
                "(RecipientUserID, TrialSeriesID, CreatedAt, ReadAt, Message, "
                "NotificationType, PayloadExperimentRequestID) "
                "VALUES (?, NULL, NOW(), NULL, ?, 'experiment_request', ?)",
                [recipient_user_id, message, request_id],
            )
        else:
            _execute(
                "INSERT INTO tblNotification "
                "(RecipientUserID, TrialSeriesID, CreatedAt, ReadAt, Message, NotificationType) "
                "VALUES (?, NULL, NOW(), NULL, ?, 'experiment_request')",
                [recipient_user_id, message],
            )
        return True
    except Exception as e:
        print(f"[Notification] ExperimentRequest-Insert fehlgeschlagen fuer uid={recipient_user_id}: {e}")
        return False


def get_unread_count(user_id: int) -> int:
    """Gibt die Anzahl ungelesener Notifications für einen User zurück."""
    if not _tables_ready():
        return 0
    try:
        rows = fetch_all(
            "SELECT COUNT(*) AS cnt FROM tblNotification "
            "WHERE RecipientUserID = ? AND ReadAt IS NULL",
            [user_id],
        )
        return int(rows[0]["cnt"]) if rows else 0
    except Exception:
        return 0



def get_total_count(user_id: int) -> int:
    """Gibt die Gesamtanzahl aller Notifications für einen User zurück (gelesen + ungelesen)."""
    if not _tables_ready():
        return 0
    try:
        rows = fetch_all(
            "SELECT COUNT(*) AS cnt FROM tblNotification WHERE RecipientUserID = ?",
            [user_id],
        )
        return int(rows[0]["cnt"]) if rows else 0
    except Exception:
        return 0


def get_series_nav_info(series_id: int) -> Optional[dict]:
    """Gibt exp_pk, series_pk und experiment_id für eine TrialSeries zurück.

    Returns:
        dict mit Schlüsseln exp_pk, series_pk, experiment_id oder None.
    """
    try:
        rows = fetch_all(
            """
            SELECT
                ts.ID          AS series_pk,
                e.ID           AS exp_pk,
                e.ExperimentID AS experiment_id
            FROM tblTrialSeries ts
            LEFT JOIN tblExperimente e ON e.ID = ts.ExperimentID
            WHERE ts.ID = ?
            LIMIT 1
            """,
            [series_id],
        )
        if rows:
            return {
                "series_pk": int(rows[0].get("series_pk") or 0),
                "exp_pk": int(rows[0].get("exp_pk") or 0),
                "experiment_id": str(rows[0].get("experiment_id") or ""),
            }
    except Exception:
        pass
    return None


def get_notifications(user_id: int, limit: int = 50) -> List[dict]:
    """Lädt alle Notifications für einen User (ungelesen zuerst).

    Joined mit tblTrialSeries und tblExperimente für Anzeige-Infos.
    """
    if not _tables_ready():
        return []
    notif_cols = _columns_map("tblnotification")
    payload_cols = (
        "n.PayloadYarnID, n.PayloadCharge,"
        if "payloadyarnid" in notif_cols
        else "NULL AS PayloadYarnID, NULL AS PayloadCharge,"
    )
    payload_cols += (
        "n.PayloadExperimentRequestID,"
        if "payloadexperimentrequestid" in notif_cols
        else "NULL AS PayloadExperimentRequestID,"
    )
    try:
        return fetch_all(
            f"""
            SELECT
                n.ID,
                n.TrialSeriesID,
                n.CreatedAt,
                n.ReadAt,
                n.Message,
                n.NotificationType,
                {payload_cols}
                ts.SeriesName,
                e.ExperimentID AS ExperimentIDTxt
            FROM tblNotification n
            LEFT JOIN tblTrialSeries ts ON ts.ID = n.TrialSeriesID
            LEFT JOIN tblExperimente e ON e.ID = ts.ExperimentID
            WHERE n.RecipientUserID = ?
            ORDER BY n.ReadAt IS NULL DESC, n.CreatedAt DESC, n.ID DESC
            LIMIT ?
            """,
            [user_id, limit],
        )
    except Exception:
        return []


def mark_as_read(notification_id: int) -> None:
    """Markiert eine einzelne Notification als gelesen."""
    try:
        _execute(
            "UPDATE tblNotification SET ReadAt = NOW() "
            "WHERE ID = ? AND ReadAt IS NULL",
            [notification_id],
        )
    except Exception:
        pass


def mark_all_as_read(user_id: int) -> None:
    """Markiert alle Notifications eines Users als gelesen."""
    try:
        _execute(
            "UPDATE tblNotification SET ReadAt = NOW() "
            "WHERE RecipientUserID = ? AND ReadAt IS NULL",
            [user_id],
        )
    except Exception:
        pass