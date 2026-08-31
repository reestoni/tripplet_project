import json
import os
import pathlib
import re
import shutil
import sys
import threading
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple

"""DB-Zugriffsschicht (MySQL).

Diese Datei war früher für Access/ODBC. Sie wurde auf MySQL umgestellt.

Wichtig: Viele Screens enthalten noch Access-SQL (eckige Klammern, True/False,
Tabellen-/Spaltennamen mit Leerzeichen). Um möglichst wenig Code anfassen zu
müssen, wird SQL beim Execute automatisch in MySQL-Syntax übersetzt.

Credentials werden NICHT im Klartext gespeichert, sondern aus einer
Fernet-verschlüsselten db_secrets.enc geladen. Der Master-Key kommt aus
secrets.enc (identisch zu advisor_worker.py).

Suchreihenfolge für db_secrets.enc:
  1. sys._MEIPASS (PyInstaller-Bundle, eingebettet)
  2. Neben der .exe / neben connection.py
  3. C:\\ProgramData\\TrippleT\\db_secrets.enc
  4. Pfad aus Umgebungsvariable TRIPPLET_SECRETS_PATH (optional, .enc oder .json)

Fallback (Dev ohne secrets.enc): db_secrets.json wie bisher (Reihenfolge analog).
"""


# =====================================================================
# TrippleT MySQL MODUS (prod / dev / dev_local)
# ---------------------------------------------------------------------
#   MODE = "prod"       → tripplet (Server)
#   MODE = "dev"        → tripplet_dev (Server)
#   MODE = "dev_local"  → tripplet_dev_local (localhost)
#
# In der gebauten .exe (PyInstaller, sys.frozen=True) ist der Modus IMMER
# "prod", mit EINER gezielten Ausnahme: TRIPPLET_MODE=offline wird auch dort
# durchgelassen (siehe Offline-Sync-Feature, CLAUDE.md) - "dev"/"dev_local"
# bleiben für die .exe weiterhin komplett blockiert, auch bei versehentlich
# gesetzter Umgebungsvariable. Ausgelöst über einen separaten Shortcut/
# Wrapper-Skript für die wenigen Superuser, die offline arbeiten dürfen
# (Zugriff wird zusätzlich nach dem Login per AccessLevel geprüft, siehe
# main.py._on_login_success - dieser Modus-Schalter ist nur der Trigger,
# nicht die eigentliche Zugriffskontrolle).
# Im Quellcode-Start (PyCharm/python main.py) fragt main.py den Modus ab
# und setzt TRIPPLET_MODE entsprechend; ohne diese Variable ist "prod" der
# sichere Default (z.B. beim direkten Ausführen von connection.py/Tests).
# =====================================================================

if getattr(sys, "frozen", False):
    MODE = "offline" if os.environ.get("TRIPPLET_MODE") == "offline" else "prod"
else:
    MODE = os.environ.get("TRIPPLET_MODE", "prod")


# =====================================================================
# Secrets laden
# =====================================================================

def _load_master_key() -> Optional[bytes]:
    """Lädt den Fernet Master-Key aus secrets.enc (identisch zu advisor_worker.py)."""
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(pathlib.Path(sys._MEIPASS) / "secrets.enc")
        candidates.append(pathlib.Path(sys.executable).parent / "secrets.enc")
    else:
        candidates.append(pathlib.Path(__file__).parent.parent / "secrets.enc")
        candidates.append(pathlib.Path("secrets.enc"))

    for p in candidates:
        if p.exists():
            try:
                key = p.read_bytes().strip()
                if len(key) == 44:
                    return key
            except Exception:
                pass
    return None


def _load_secrets() -> Dict[str, Any]:
    """Lädt DB-Credentials aus db_secrets.enc (Fernet) mit Fallback auf db_secrets.json (Dev).

    Suchreihenfolge für db_secrets.enc:
      1. sys._MEIPASS  (eingebettet ins PyInstaller-Bundle)
      2. Neben der .exe / neben connection.py
      3. C:\\ProgramData\\TrippleT\\db_secrets.enc
      4. TRIPPLET_SECRETS_PATH (Umgebungsvariable)

    Fallback (nur Dev, wenn kein secrets.enc vorhanden):
      db_secrets.json an denselben Orten.
    """
    master_key = _load_master_key()

    # ── Basispfade ────────────────────────────────────────────────────────────
    if getattr(sys, "frozen", False):
        base = pathlib.Path(sys.executable).parent
        meipass = pathlib.Path(sys._MEIPASS)
    else:
        base = pathlib.Path(__file__).parent
        meipass = None

    env_path = os.environ.get("TRIPPLET_SECRETS_PATH")

    # ── Verschlüsselte .enc-Kandidaten ───────────────────────────────────────
    enc_candidates: list[pathlib.Path] = []
    if meipass:
        enc_candidates.append(meipass / "db_secrets.enc")     # Bundle (primär)
    enc_candidates.append(base / "db_secrets.enc")
    enc_candidates.append(pathlib.Path(r"C:\ProgramData\TrippleT\db_secrets.enc"))
    if env_path and env_path.endswith(".enc"):
        enc_candidates.insert(0, pathlib.Path(env_path))

    if master_key:
        from cryptography.fernet import Fernet, InvalidToken
        f = Fernet(master_key)
        for p in enc_candidates:
            if p.exists():
                try:
                    plaintext = f.decrypt(p.read_bytes())
                    return json.loads(plaintext.decode("utf-8"))
                except InvalidToken:
                    raise ValueError(
                        f"db_secrets.enc ({p}) konnte nicht entschlüsselt werden.\n"
                        "Bitte encrypt_db_secrets.py erneut ausführen."
                    )
                except json.JSONDecodeError as e:
                    raise ValueError(f"db_secrets.enc enthält kein gültiges JSON nach Entschlüsselung: {e}") from e

    # ── Fallback: Klartext-JSON (Dev ohne secrets.enc) ────────────────────────
    json_candidates: list[pathlib.Path] = []
    json_candidates.append(base / "db_secrets.json")
    json_candidates.append(pathlib.Path(r"C:\ProgramData\TrippleT\db_secrets.json"))
    if env_path and not env_path.endswith(".enc"):
        json_candidates.insert(0, pathlib.Path(env_path))

    for p in json_candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            except json.JSONDecodeError as e:
                raise ValueError(f"db_secrets.json ist kein gültiges JSON ({p}): {e}") from e

    # ── Nichts gefunden ───────────────────────────────────────────────────────
    searched_enc  = "\n  ".join(str(p) for p in enc_candidates)
    searched_json = "\n  ".join(str(p) for p in json_candidates)
    raise FileNotFoundError(
        "Keine DB-Credentials gefunden.\n\n"
        f"Gesucht (db_secrets.enc):\n  {searched_enc}\n\n"
        f"Gesucht (db_secrets.json, Fallback):\n  {searched_json}\n\n"
        "Lösung: encrypt_db_secrets.py im Projektordner ausführen."
    )


_SECRETS = _load_secrets()

_DEV_MODE: bool = False
_DEV_LOCAL_MODE: bool = False
_OFFLINE_MODE: bool = False


def _offline_sqlite_path() -> pathlib.Path:
    """Path to the local offline SQLite file.

    TRIPPLET_OFFLINE_DB_PATH overrides the path (e.g. for tests/PoC scripts,
    so they don't accidentally touch the "real" offline copy under
    %LOCALAPPDATA%). Without an override, the file lives under
    %LOCALAPPDATA%\\TrippleT, matching other Windows desktop apps.

    Routed by MODE into one of two persisted files, automatically, on BOTH
    sides of the workflow - no manual TRIPPLET_OFFLINE_DB_PATH juggling
    needed to keep them apart:
      - "prod", "offline", "offline_prod"           -> tripplet_offline_prod.sqlite
      - "dev_local", "offline_dev_local"             -> tripplet_offline_dev_local.sqlite
    "prod"/"dev_local" only matter here because this function is ALSO what
    an online "Prepare/refresh" session (pull_snapshot(), via
    get_offline_sqlite_path()) targets - preparing while running against
    prod now lands in the same file that "offline"/"offline_prod" reads
    later, with no extra step. "offline" (plain) is folded into the prod
    file rather than kept as its own third file: the real, deployed field
    flow (TrippleT_Launcher_Offline.bat, superusers) is only ever used
    against prod in practice, so it's effectively just another spelling of
    "offline_prod" - "offline_prod" is the explicit/preferred one for
    source-run dev/testing (see main.py's startup dialog), "offline" is
    what the deployed launcher's env var literally sets. Which exact
    backend a given pull actually came from is still tracked precisely
    inside the file itself regardless of its name (self-stamped by
    pull_snapshot(), see db/offline_snapshot.py's get_snapshot_source_mode())
    - merge relies on THAT, not on the filename.
    """
    env_path = os.environ.get("TRIPPLET_OFFLINE_DB_PATH")
    if env_path:
        p = pathlib.Path(env_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    base = pathlib.Path(os.environ.get("LOCALAPPDATA") or str(pathlib.Path.home())) / "TrippleT"
    base.mkdir(parents=True, exist_ok=True)
    if MODE in ("prod", "offline", "offline_prod"):
        return base / "tripplet_offline_prod.sqlite"
    if MODE in ("dev_local", "offline_dev_local"):
        return base / "tripplet_offline_dev_local.sqlite"
    return base / "tripplet_offline.sqlite"


def _resolve_db_config() -> Dict[str, Any]:
    """Ermittelt DB-Name und Verbindungsdaten anhand von MODE."""
    global _DEV_MODE, _DEV_LOCAL_MODE, _OFFLINE_MODE

    if MODE in ("offline", "offline_prod", "offline_dev_local"):
        # Offline (all three variants) counts as "safe to write" just like
        # dev_local (local SQLite file, no network connection) - existing
        # is_dev_mode() branches (local image paths etc.) apply unchanged.
        # The two "_prod"/"_dev_local" variants only differ in WHICH file
        # _offline_sqlite_path() resolves to - see that function's docstring.
        _DEV_MODE = True
        _DEV_LOCAL_MODE = True
        _OFFLINE_MODE = True
        path = _offline_sqlite_path()
        return {"sqlite_path": str(path), "db": path.stem}

    _OFFLINE_MODE = False

    if MODE not in _SECRETS:
        raise ValueError(
            f"MODE '{MODE}' nicht in db_secrets.json gefunden. "
            f"Verfügbare Modi: {list(_SECRETS.keys())}"
        )

    cfg = _SECRETS[MODE]

    if MODE == "prod":
        _DEV_MODE = False
        _DEV_LOCAL_MODE = False
    elif MODE == "dev":
        _DEV_MODE = True
        _DEV_LOCAL_MODE = False
    elif MODE == "dev_local":
        _DEV_MODE = True
        _DEV_LOCAL_MODE = True
    else:
        raise ValueError(
            f"Unbekannter MODE: {MODE!r} (erlaubt: 'prod', 'dev', 'dev_local', "
            f"'offline', 'offline_prod', 'offline_dev_local')"
        )

    return {
        "host":     cfg["host"],
        "port":     int(cfg.get("port", 3306)),
        "user":     cfg["user"],
        "password": cfg["password"],
        "db":       cfg["db"],
    }


_DB_CFG = _resolve_db_config()
DB_NAME = _DB_CFG["db"]


def is_dev_mode() -> bool:
    """True if a DEV database is currently in use (dev, dev_local, or offline)."""
    return _DEV_MODE


def is_dev_local_mode() -> bool:
    """True if dev_local or offline is currently in use."""
    return _DEV_LOCAL_MODE


def is_offline_mode() -> bool:
    """True if the local SQLite offline copy is currently in use (no MySQL)."""
    return _OFFLINE_MODE


def get_offline_sqlite_path() -> str:
    """Public accessor for the default offline SQLite file path (for UI display etc.)."""
    return str(_offline_sqlite_path())


def current_db_name() -> str:
    """Gibt den aktuell verwendeten DB-Namen (DEV oder PROD) zurück."""
    return DB_NAME


def new_global_id() -> str:
    """Erzeugt eine neue globale GUID als String (36 Zeichen)."""
    return str(uuid.uuid4())


def raw_mysql_connect(mode: str):
    """Opens a raw MySQL connection for an arbitrary mode, INDEPENDENT of the
    currently active MODE (which is fixed per process, see above).

    Only meant for cross-mode tools (offline schema introspection, snapshot
    pull: the process runs with TRIPPLET_MODE=offline but briefly also needs
    a MySQL source to read from). No pooling, no SQL translation - a
    deliberately thin raw connection, meant only for read-only introspection/
    snapshot purposes.
    """
    import mysql.connector
    if mode not in _SECRETS:
        raise ValueError(f"Mode '{mode}' not found in secrets. Available: {list(_SECRETS.keys())}")
    cfg = _SECRETS[mode]
    return mysql.connector.connect(
        host=cfg["host"],
        port=int(cfg.get("port", 3306)),
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["db"],
        autocommit=True,
        connect_timeout=_CONNECT_TIMEOUT_SECONDS,
    )


_POOL = None
_POOL_LOCK = threading.Lock()
_POOL_SIZE = 5
# Verhindert lange (OS-Default-)Haenger bei unerreichbarem Host - vorher war
# gar kein Timeout gesetzt, ein Netz-Hänger führte zu ~20s+ Warten ohne
# jede Rückmeldung (siehe TestLoginScreenSicherheit-Timing).
_CONNECT_TIMEOUT_SECONDS = 10


def _get_pool():
    """Lazy erzeugter Connection-Pool (ein Prozess = eine feste DB-Config, siehe MODE oben)."""
    global _POOL
    if _POOL is None:
        with _POOL_LOCK:
            if _POOL is None:
                from mysql.connector import pooling
                _POOL = pooling.MySQLConnectionPool(
                    pool_name="tripplet_pool",
                    pool_size=_POOL_SIZE,
                    host=_DB_CFG["host"],
                    port=_DB_CFG["port"],
                    user=_DB_CFG["user"],
                    password=_DB_CFG["password"],
                    database=current_db_name(),
                    autocommit=True,
                    connect_timeout=_CONNECT_TIMEOUT_SECONDS,
                )
    return _POOL


def _get_sqlite_connection(path: str | None = None):
    """Opens a fresh connection to a local SQLite file (default: the offline copy).

    No pooling like MySQL: SQLite is a local file, connecting doesn't cost a
    network round-trip. Instead, a fresh connection is opened on every call -
    this also sidesteps thread-affinity issues (sqlite3 connections are
    otherwise bound to the thread that created them).
    isolation_level=None = autocommit, matching autocommit=True on the MySQL pool.
    """
    import sqlite3
    cn = sqlite3.connect(path or str(_offline_sqlite_path()), isolation_level=None, check_same_thread=False)
    cn.execute("PRAGMA foreign_keys = ON")
    # SQLite 3.34+ defaults recursive_triggers to ON, which would make the
    # edit-tracking trigger (see offline_schema.generate_update_trigger_sql)
    # re-fire on its own bookkeeping UPDATE and recurse. Off is what every
    # SQLite version before 3.34 did anyway, so this is a deliberate pin, not
    # a workaround for something fragile.
    cn.execute("PRAGMA recursive_triggers = OFF")
    return cn


def raw_sqlite_connect(path: str | None = None) -> "_SQLiteConnWrapper":
    """Opens a translating connection to a local SQLite file, INDEPENDENT of the
    currently active MODE (default: the offline copy at _offline_sqlite_path()).

    Mirrors raw_mysql_connect() on the other side: the offline schema/snapshot/
    merge tools need to target the offline SQLite file regardless of whether
    the process itself happens to be running online or offline - "prepare
    offline copy" is clicked while online, and "merge changes back" runs in a
    later online session, reading a file written by a separate offline
    session. Neither operation can rely on is_offline_mode()/get_connection()
    being wired to the right backend.
    """
    return _SQLiteConnWrapper(_get_sqlite_connection(path))


class _SQLiteCursorWrapper:
    """SQLite cursor wrapper that translates SQL before execute (same API as _CursorWrapper)."""

    def __init__(self, cur):
        self._cur = cur

    @property
    def description(self):
        return self._cur.description

    @property
    def rowcount(self):
        return getattr(self._cur, "rowcount", 0)

    @property
    def lastrowid(self):
        return getattr(self._cur, "lastrowid", None)

    def execute(self, sql: str, params: Iterable[Any] | None = None):
        return self._cur.execute(_to_sqlite_sql(sql), tuple(params or ()))

    def executemany(self, sql: str, seq_params: Iterable[Iterable[Any]]):
        return self._cur.executemany(_to_sqlite_sql(sql), [tuple(p) for p in (seq_params or [])])

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def close(self):
        try:
            self._cur.close()
        except Exception:
            pass


class _SQLiteConnWrapper:
    """Connection wrapper for the local offline SQLite file (same API as _ConnWrapper)."""

    def __init__(self, cn):
        self._cn = cn

    def cursor(self, *args, **kwargs):
        return _SQLiteCursorWrapper(self._cn.cursor())

    def commit(self):
        return self._cn.commit()

    def rollback(self):
        return self._cn.rollback()

    def close(self):
        return self._cn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.close()
        except Exception:
            pass
        return False


def get_connection():
    """Gets a connection - depending on MODE, either from the MySQL pool or as
    a fresh local SQLite offline connection.

    Holt eine MySQL-Connection aus einem Pool (statt bei jedem Aufruf neu zu verbinden).

    Vorher wurde für JEDEN einzelnen DB-Zugriff eine frische TCP-Verbindung
    aufgebaut und am Ende wieder geschlossen - Screens mit vielen
    Einzelqueries (z.B. ShowExperimentScreen) haben so dutzende
    Verbindungsaufbauten pro Laden verursacht. Der Pool hält bis zu
    _POOL_SIZE Verbindungen offen und reicht sie wieder; _ConnWrapper.close()
    gibt die Verbindung nur an den Pool zurück (kein echtes Schliessen) -
    für Aufrufer ändert sich nichts, `with get_connection() as cn:` bleibt
    das erwartete Nutzungsmuster.

    ping(reconnect=True) prüft/repariert eine evtl. inzwischen tot gegangene
    (z.B. durch Firewall-Idle-Timeout gekappte) Pool-Verbindung, bevor sie
    zurückgegeben wird.

    Hinweis: Damit sich bestehender Code wie bisher verhält, ist autocommit=True.
    """
    if _OFFLINE_MODE:
        return _SQLiteConnWrapper(_get_sqlite_connection())

    cn = _get_pool().get_connection()
    try:
        cn.ping(reconnect=True, attempts=1, delay=0)
    except Exception:
        pass
    return _ConnWrapper(cn)


# ------------------------- SQL Translation -------------------------

# --- Tabellen-Mapping (Access → MySQL) ---
TABLE_MAP = {
    "tblAirChannelShape": "tblairchannelshape",
    "tblairchannelshape": "tblairchannelshape",
    "tbldtyjets": "tbljets",
    "tblDTYJets": "tbljets",
    "tbldtyseries": "tblseries",
    "tblDTYSeries": "tblseries",
    "tblMaschineFields": "tblmachinefields",
    "tblMachineFields": "tblmachinefields",
    "tblmaschinenfields": "tblmachinefields",
    "tblmachinefields": "tblmachinefields",
}

def _map_table_name(name: str) -> str:
    """Mappt Access-Tabellennamen auf MySQL-Tabellennamen (case-insensitive)."""
    if not name:
        return name
    # direkter Treffer
    if name in TABLE_MAP:
        return TABLE_MAP[name]
    low = name.lower()
    # case-insensitive Treffer
    for k, v in TABLE_MAP.items():
        if k.lower() == low:
            return v
    return name


# Access → MySQL: Identifiers, die in MySQL anders heissen
_IDENT_MAP = {    "tblJets": "tbljets",
    "tblExperimente": "tblexperimente",
    "tblMaschine": "tblmaschine",
    "tblYarn": "tblyarn",
    "tblUser": "tbluser",
    "tblTrialSeriesYarn": "tbltrialseriesyarn",
    "tblTrialSeries": "tbltrialseries",
    "tblTrial": "tbltrial",
    "tblTrialSeriesImage": "tbltrialseriesimage",
    "tblTrialSeriesPDF": "tbltrialseriespdf",
    "tblMachineFields": "tblmachinefields",

    "Air Channel Shape": "AirChannelShape",
    "DTY Series": "Series",
    "Experiment ID": "ExperimentID",
    "Titer (dtex)": "Titer",
    "Username": "UserName",
    "Intermingling Points (FP/m)": "FPm",
    "FP/m": "FPm",
    "Stability CV (%)": "StabilityCV",
    "Stability (%)": "Stability",
    "Intermingling Points CV": "FPmCV",
    "Intermingling Points CV (%)": "FPmCV",
    "SPD Avg": "AvgSPD",
    "SPD Std": "StdDevSPD",
    "SPD Dev": "StdDevSPD",
    "SPD StdDev": "StdDevSPD",
    "Tension (cN/dtex)": "Tension",
    "Yarn Tension (cN)": "YarnTension",
    "Tension (cN)": "Tension",
    "OL X (mm)": "OLX",
    "OL S": "OLS",
    "OL X": "OLX",
    "KL S (mm)": "KLS",
    "KL X (mm)": "KLX",
    "OL S (mm)": "OLS",

}


_re_bracket_ident = re.compile(r"\[([^\]]+)\]")
_re_backtick_ident = re.compile(r"`([^`]+)`")
_re_tbl_token = re.compile(r"\btbl[A-Za-z0-9_]+\b")


def _normalize_identifiers(sql: str) -> str:
    """Converts "Access-ish" SQL identifiers/literals into a backend-neutral form.

    Shared core for the MySQL and SQLite translation (placeholder handling is
    the only thing that differs between the two backends - SQLite understands
    square brackets, backticks AND '?' placeholders natively, MySQL doesn't):
    - square brackets → backticks
    - True/False → 1/0
    - tblXxx tokens → lowercase (for case-sensitive Linux MySQL setups; a
      no-op for SQLite, since identifier comparisons there are case-insensitive
      anyway, but harmless)
    """
    if not sql:
        return sql

    s = sql

    # Booleans
    s = re.sub(r"\bTrue\b", "1", s, flags=re.IGNORECASE)
    s = re.sub(r"\bFalse\b", "0", s, flags=re.IGNORECASE)

    # Bracket-Identifiers → Backticks + Mapping
    def _br(m: re.Match) -> str:
        name = (m.group(1) or "").strip()
        # Support Access-style identifiers like [R.SPD Avg] where 'R' is a table alias.
        if "." in name:
            left, right = name.split(".", 1)
            left = left.strip()
            right = right.strip()
            right_mapped = _IDENT_MAP.get(right, right)
            return f"`{left}`.`{right_mapped}`"

        mapped = _IDENT_MAP.get(name, name)
        return f"`{mapped}`"

    s = _re_bracket_ident.sub(_br, s)

    # Backtick-Identifiers → Backticks + Mapping (für Queries, die bereits `...` nutzen)
    def _bt(m: re.Match) -> str:
        name = (m.group(1) or "").strip()
        if "." in name:
            left, right = name.split(".", 1)
            left = left.strip()
            right = right.strip()
            right_mapped = _IDENT_MAP.get(right, right)
            return f"`{left}`.`{right_mapped}`"

        mapped = _IDENT_MAP.get(name, name)
        return f"`{mapped}`"

    s = _re_backtick_ident.sub(_bt, s)

    # Tabellen-Namen tblXxx → lowercase
    s = _re_tbl_token.sub(lambda m: m.group(0).lower(), s)

    # Tabellen-Mapping (Access → MySQL)
    for src_tbl, dst_tbl in TABLE_MAP.items():
        s = re.sub(rf"\b{re.escape(src_tbl)}\b", dst_tbl, s, flags=re.IGNORECASE)

    return s


def _to_mysql_sql(sql: str) -> str:
    """Converts "Access-ish" SQL to MySQL (identifier normalization + '?' → '%s')."""
    if not sql:
        return sql
    s = _normalize_identifiers(sql)
    if "?" in s:
        s = s.replace("?", "%s")
    return s


_re_at_identity = re.compile(r"@@IDENTITY\b", re.IGNORECASE)
_re_last_insert_id = re.compile(r"\bLAST_INSERT_ID\s*\(\s*\)", re.IGNORECASE)
_re_now_func = re.compile(r"\bNOW\s*\(\s*\)", re.IGNORECASE)


def _to_sqlite_sql(sql: str) -> str:
    """Converts "Access-ish" SQL to SQLite.

    SQLite understands '?' placeholders, square brackets AND backticks
    natively (MS Access compatibility), so only the shared identifier/boolean
    normalization is left here - no placeholder translation needed (unlike
    MySQL).

    Two real exceptions, both MySQL functions with no SQLite equivalent under
    the same name, translated here so existing code stays unchanged:
    - `SELECT @@IDENTITY` / `LAST_INSERT_ID()` - MySQL/Access-ODBC idiom for
      "ID of the last insert statement on this connection" (~19 call sites
      across 12 screens) -> SQLite's last_insert_rowid().
    - `NOW()` - used for Timestamp columns in ~6 files (e.g. lab-table saves
      in screen_show_experiment.py's save_dirty()) -> SQLite's datetime('now')
      (returns 'YYYY-MM-DD HH:MM:SS', same shape MySQL's NOW() produces).
    """
    if not sql:
        return sql
    s = _normalize_identifiers(sql)
    s = _re_at_identity.sub("last_insert_rowid()", s)
    s = _re_last_insert_id.sub("last_insert_rowid()", s)
    s = _re_now_func.sub("datetime('now')", s)
    return s


class _CursorWrapper:
    """Cursor-Wrapper, der SQL vor dem Execute übersetzt."""

    def __init__(self, cur):
        self._cur = cur

    # ---- Proxy-Properties ----
    @property
    def description(self):
        return self._cur.description

    @property
    def rowcount(self):
        return getattr(self._cur, "rowcount", 0)

    @property
    def lastrowid(self):
        """Proxy für lastrowid (wichtig für INSERTs mit Auto-Increment)."""
        return getattr(self._cur, "lastrowid", None)

    # ---- Execute ----
    def execute(self, sql: str, params: Iterable[Any] | None = None):
        return self._cur.execute(_to_mysql_sql(sql), params or ())

    def executemany(self, sql: str, seq_params: Iterable[Iterable[Any]]):
        return self._cur.executemany(_to_mysql_sql(sql), list(seq_params or []))

    # ---- Fetch ----
    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def close(self):
        try:
            self._cur.close()
        except Exception:
            pass


class _ConnWrapper:
    """Connection-Wrapper für Context-Manager + SQL-übersetzende Cursor."""

    def __init__(self, cn):
        self._cn = cn

    def cursor(self, *args, **kwargs):
        return _CursorWrapper(self._cn.cursor(*args, **kwargs))

    def commit(self):
        return self._cn.commit()

    def rollback(self):
        return self._cn.rollback()

    def close(self):
        return self._cn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.close()
        except Exception:
            pass
        return False

# ---------- Helpers für generische Queries ----------


def _normalize_sql(sql: str) -> str:
    """Erlaubt sowohl '%s' als auch '?' als Platzhalter.

    Die eigentliche Normalisierung passiert in _to_mysql_sql() (CursorWrapper).
    Diese Funktion bleibt als No-Op für API-Kompatibilität.
    """
    return sql


def fetch_all(sql: str, params: Iterable[Any] | None = None) -> List[Dict[str, Any]]:
    """SELECT → Liste von Dicts (spaltenname->wert)."""
    sql = _normalize_sql(sql)
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql, list(params or []))
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in rows]


def execute(sql: str, params: Iterable[Any] | None = None) -> int:
    """Einzelnes INSERT/UPDATE/DELETE → rowcount (mit commit)."""
    sql = _normalize_sql(sql)
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql, list(params or []))
        try:
            cn.commit()
        except Exception:
            pass
        return getattr(cur, "rowcount", 0) or 0


def execute_insert(sql: str, params: Iterable[Any] | None = None) -> Optional[int]:
    """INSERT -> neue Auto-Increment-ID (oder None), zuverlässig auf EINER
    Session/Connection ermittelt (`cur.lastrowid`).

    Ersetzt das im Projekt bisher verbreitete Muster `execute(insert_sql, ...)`
    gefolgt von einem separaten `fetch_all('SELECT @@IDENTITY AS NewID')` (bzw.
    `LAST_INSERT_ID()`) - @@IDENTITY/LAST_INSERT_ID() sind reine
    Session-State pro MySQL-Verbindung, execute()/fetch_all() ziehen sich aber
    JEWEILS unabhängig eine (nicht notwendigerweise dieselbe) Verbindung aus
    dem Pool (siehe get_connection() oben), wodurch die zweite Abfrage
    gelegentlich auf einer frischen Connection landet und dort fälschlich 0
    zurückgibt. Empirisch nachgewiesen (nicht nur vermutet) beim Bau von
    quick_add_colour() in screen_manage_yarn.py, 2026-08-24 - ein Testlauf mit
    mehreren schnell aufeinanderfolgenden execute()+fetch_all(@@IDENTITY)-Paaren
    lieferte dabei reproduzierbar einmal 0 statt der echten neuen ID. Dieselbe
    Funktion deckt beide Modi ab (MySQL pooled UND SQLite offline) - der
    zugrundeliegende `_CursorWrapper.lastrowid` reicht in beiden Fällen bereits
    korrekt durch."""
    sql = _normalize_sql(sql)
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql, list(params or []))
        try:
            cn.commit()
        except Exception:
            pass
        new_id = getattr(cur, "lastrowid", None)
    return int(new_id) if new_id else None


def executemany(sql: str, seq_params: Iterable[Iterable[Any]]) -> int:
    """executemany → rowcount (Treiberabhängig, mit commit)."""
    sql = _normalize_sql(sql)
    with get_connection() as cn:
        cur = cn.cursor()
        cur.executemany(sql, list(seq_params or []))
        return getattr(cur, "rowcount", 0) or 0


# ---------- Schema-Helpers (MySQL) ----------

# Process-lifetime caches for table_exists()/get_columns_map(), keyed on
# (name, schema). Schema only ever changes via a deliberate DDL migration
# (never through normal app usage), so a stale cache within one running
# session isn't a realistic risk - matches the existing "MODE is fixed once
# at process start" assumption elsewhere in this file. Profiled: opening a
# single ShowExperimentScreen experiment hits these dozens of times (once
# per lab tab builder, each an uncached information_schema round trip) -
# see CLAUDE.md's offline-sync section for the same round-trip-count concern
# over a real remote connection.
_TABLE_EXISTS_CACHE: Dict[Tuple[str, str], bool] = {}
_COLUMNS_MAP_CACHE: Dict[Tuple[str, str], Dict[str, str]] = {}


def table_exists(name: str, schema: str | None = None) -> bool:
    """True, wenn die Tabelle existiert. Siehe _TABLE_EXISTS_CACHE oben."""
    if not name:
        return False

    cache_key = (name.lower(), schema or current_db_name())
    cached = _TABLE_EXISTS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if _OFFLINE_MODE:
        rows = fetch_all(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND lower(name) = ? LIMIT 1",
            (_map_table_name(name).lower(),),
        )
        result = bool(rows)
    else:
        schema_val = schema or current_db_name()
        rows = fetch_all(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
            LIMIT 1
            """,
            (schema_val, _map_table_name(name).lower()),
        )
        result = bool(rows)

    _TABLE_EXISTS_CACHE[cache_key] = result
    return result


def get_columns_map(table: str, schema: str | None = None) -> Dict[str, str]:
    """{lower_name: real_name} für eine Tabelle. Siehe _COLUMNS_MAP_CACHE oben.

    Returns a fresh copy on every call (never the cached dict itself), so a
    caller mutating the result can't corrupt the shared cache.
    """
    cache_key = (table.lower(), schema or current_db_name())
    cached = _COLUMNS_MAP_CACHE.get(cache_key)
    if cached is not None:
        return dict(cached)

    if _OFFLINE_MODE:
        out: Dict[str, str] = {}
        with get_connection() as cn:
            cur = cn.cursor()
            # PRAGMA doesn't support '?' placeholders for the table name.
            safe_name = _map_table_name(table).replace('"', "")
            cur.execute(f'PRAGMA table_info("{safe_name}")')
            for r in cur.fetchall():
                col = r[1]  # PRAGMA table_info: (cid, name, type, notnull, dflt_value, pk)
                if col is not None:
                    out[str(col).lower()] = str(col)
        _COLUMNS_MAP_CACHE[cache_key] = out
        return dict(out)

    schema_val = schema or current_db_name()
    rows = fetch_all(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """,
        (schema_val, _map_table_name(table).lower()),
    )
    out: Dict[str, str] = {}
    for r in rows:
        # je nach Connector können die Dict-Keys unterschiedlich gross/klein sein
        if isinstance(r, dict):
            col = r.get("column_name")
            if col is None:
                col = r.get("COLUMN_NAME")
            if col is None:
                # Fallback: erster Wert im Dict
                try:
                    col = next(iter(r.values()))
                except Exception:
                    col = None
        else:
            col = r[0]
        if col is not None:
            out[str(col).lower()] = str(col)
    _COLUMNS_MAP_CACHE[cache_key] = out
    return dict(out)


# ------------------------- Password hashing (Argon2) -------------------------

def hash_password(plain_password: str) -> str:
    """Erzeugt einen Argon2-Hash für ein Klartext-Passwort."""
    from argon2 import PasswordHasher
    ph = PasswordHasher()  # sichere Defaults
    return ph.hash(plain_password)


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Prüft Klartext gegen gespeicherten Argon2-Hash."""
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError

    ph = PasswordHasher()
    try:
        return ph.verify(stored_hash, plain_password)
    except VerifyMismatchError:
        return False


def get_user_password_hash(username: str):
    """Gibt pw_hash zurück (oder None)."""
    if not username:
        return None
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute("SELECT [pw_hash] FROM tblUser WHERE [Username]=?", (username,))
        row = cur.fetchone()
        return row[0] if row else None


def verify_user_password(username: str, password: str) -> bool:
    """True, wenn Passwort für User korrekt ist (via pw_hash)."""
    if not username or not password:
        return False
    pw_hash = get_user_password_hash(username)
    if not pw_hash:
        return False
    return verify_password(password, pw_hash)


# ---------- Original-Funktionen (API kompatibel) ----------
def check_credentials(username: str, password: str) -> bool:
    """True, wenn Username/Passwort korrekt ist UND Active=True."""
    if not username or not password:
        return False

    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            "SELECT [pw_hash], [Active] FROM tblUser WHERE [Username]=?",
            (username,),
        )
        row = cur.fetchone()
        if not row:
            return False

        pw_hash, active = row[0], bool(row[1])
        if not pw_hash:
            return False

        return bool(active) and verify_password(password, pw_hash)



def is_user_active(username: str) -> bool:
    """True, wenn tblUser.Active = True/1 für diesen User."""
    if not username:
        return False
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            "SELECT [Active] FROM tblUser WHERE [Username]=?", (username,))
        row = cur.fetchone()
        return bool(row[0]) if row else False


def user_exists(username: str) -> bool:
    """True, wenn Username in tblUser existiert."""
    if not username:
        return False
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute("SELECT 1 FROM tblUser WHERE [Username]=?", (username,))
        return cur.fetchone() is not None


def get_user_password(username: str):
    """DEPRECATED: Klartext-Passwörter werden nicht mehr unterstützt."""
    return None



def update_user_password(username: str, new_password: str) -> bool:
    """Passwort setzen (speichert Argon2-Hash in pw_hash); True bei Erfolg."""
    if not username or not new_password:
        return False

    new_hash = hash_password(new_password)

    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            "UPDATE tblUser SET [pw_hash]=? WHERE [Username]=?",
            (new_hash, username),
        )
        return cur.rowcount > 0



def get_user_access_level(username: str) -> int:
    """Liest tblAccessRight.AccessLevel (int) über tblUser.AccessRights → tblAccessRight.ID.

    Gibt 0 zurück, wenn kein Treffer oder Feld fehlt.
    """
    if not username:
        return 0
    with get_connection() as cn:
        cur = cn.cursor()
        try:
            cur.execute(
                "SELECT ar.[AccessLevel] "
                "FROM (tblUser AS u "
                "INNER JOIN tblAccessRight AS ar ON u.[AccessRights]=ar.[ID]) "
                "WHERE u.[Username]=?",
                (username,),
            )
            row = cur.fetchone()
        except Exception:
            return 0
        if not row:
            return 0
        try:
            return int(row[0] or 0)
        except Exception:
            try:
                return int(float(row[0]))
            except Exception:
                return 0


def get_user_access_right(username: str):
    """Liest tblAccessRight.AccessRight (Text) über tblUser.AccessRights → tblAccessRight.ID.

    Gibt None zurück, wenn kein Treffer.
    """
    if not username:
        return None
    with get_connection() as cn:
        cur = cn.cursor()
        try:
            cur.execute(
                "SELECT ar.[AccessRight] "
                "FROM (tblUser AS u "
                "INNER JOIN tblAccessRight AS ar ON u.[AccessRights]=ar.[ID]) "
                "WHERE u.[Username]=?",
                (username,),
            )
            row = cur.fetchone()
        except Exception:
            return None
        if not row:
            return None
        val = row[0]
        return str(val) if val is not None else None


def get_user_admin(username: str) -> bool:
    """True, wenn tblUser.AccessLevel >= 3 für diesen User."""
    return get_user_access_level(username) >= 3


def get_user_admin_box(username: str) -> bool:
    """True, wenn tblUser.AdminBox = True/1 für diesen User.

    Dieses Flag ist ein *zusätzliches* Recht (unabhängig vom AccessLevel),
    damit ausgewählte User die Admin-Box sehen *und* die Admin-Funktionen
    nutzen können.
    """
    if not username:
        return False
    with get_connection() as cn:
        cur = cn.cursor()
        try:
            cur.execute(
                "SELECT [AdminBox] FROM tblUser WHERE [Username]=?",
                (username,),
            )
            row = cur.fetchone()
        except Exception:
            return False
        if not row:
            return False
        val = row[0]
        # Access/ACE liefert je nach Treiber True/False, -1/0 oder 1/0
        if isinstance(val, bool):
            return bool(val)
        try:
            return int(val) != 0
        except Exception:
            return str(val).strip().lower() in {"true", "yes", "ja", "-1", "1"}


def fetch_experiments_with_series(maschine_id: int | None = None):
    """
    Übersicht für screen_all_experiments – inkludiert auch Einträge ohne CreationDate
    oder ohne BacklogOwner (LEFT JOINs).
    In der Rückgabe ist "owner" der Username aus tblUser, basierend auf tblTrialSeries.BacklogOwner,
    und "backlog_status_id" der numerische Status aus tblBacklogStatus.
    """
    params: List[Any] = []
    where = ""
    if maschine_id is not None:
        where = "WHERE s.[MachineID] = ?"
        params.append(maschine_id)

    # Wichtig: In Access/ACE müssen bei kombinierten (LEFT/INNER) JOINs die Klammern exakt gesetzt sein.
    sql = f"""
        SELECT
            e.[ID]             AS exp_id_pk,
            e.[Experiment ID]  AS experiment_id,
            s.[ID]             AS series_id_pk,
            s.[SeriesName]     AS series_name,
            m.[Maschine]        AS maschine,
            s.[CreationDate]    AS creation_date,
            u.[Username]        AS owner_username,
            s.[BacklogStatusID] AS backlog_status_id
        FROM ((tblExperimente AS e
            INNER JOIN tblTrialSeries AS s
                ON e.[ID] = s.[ExperimentID])
            LEFT JOIN tblMaschine AS m
                ON m.[ID] = s.[MachineID])
            LEFT JOIN tblUser AS u
                ON u.[ID] = s.[BacklogOwner]
        {where}
        ORDER BY e.[Experiment ID] DESC, s.[ID];
    """

    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append({
            "exp_id_pk":         r[0],
            "experiment_id":     r[1],
            "series_id_pk":      r[2],
            "series_name":       r[3],
            "maschine":          r[4],
            "creation_date":     r[5],
            "owner":             r[6],  # Owner-Username (kann None sein)
            # numerischer Backlog-Status (kann None sein)
            "backlog_status_id": r[7],
        })
    return out


def update_trialseries_name(series_id: int, new_name: str) -> int:
    """Updates tblTrialSeries.SeriesName for the given series ID.

    Returns the number of affected rows (0 if nothing changed / not found).
    """
    if not series_id:
        return 0
    new_name = (new_name or "").strip()
    if not new_name:
        return 0
    sql = "UPDATE tblTrialSeries SET [SeriesName]=? WHERE [ID]=?"
    return execute(sql, (new_name, int(series_id)))



def cleanup_draft_experiment_requests(*, created_by: Any | None, created_by_username: str | None = None) -> Dict[str, Any]:
    """Löscht unvollständige Experiment-Requests (RequestStatus IS NULL) eines Users inkl. Images-Ordner.

    Ablauf:
    - finde alle tblExperimentRequests mit RequestStatus IS NULL und CreatedBy passend
    - finde zugehörige tblExperimentRequestImage Rows (FK-Spalte kann je nach Schema variieren)
    - lösche Ordner aus RelativePath (ohne Nachfrage)
    - lösche Image-Rows und Request-Row

    Rückgabe: Statistik-Dict (für Logging/Debug).
    """
    stats: Dict[str, Any] = {
        "requests_found": 0,
        "requests_deleted": 0,
        "image_rows_deleted": 0,
        "folders_deleted": 0,
        "errors": [],
    }

    try:
        if not table_exists("tblExperimentRequests"):
            return stats
    except Exception as e:
        stats["errors"].append(f"table_exists(tblExperimentRequests): {e}")
        return stats

    # Column mapping (robust gegen Naming-Varianten)
    try:
        req_cols = get_columns_map("tblExperimentRequests")
    except Exception as e:
        stats["errors"].append(f"get_columns_map(tblExperimentRequests): {e}")
        return stats

    col_id = req_cols.get("id", "ID")
    col_status = req_cols.get("requeststatus", "RequestStatus")
    col_created_by = req_cols.get("createdby", "CreatedBy")

    # Kandidaten bestimmen: primär per UserID, fallback per Username (falls CreatedBy als Text gespeichert wäre)
    where = f"[{col_status}] IS NULL"
    params: list[Any] = []
    if created_by not in (None, ""):
        where += f" AND [{col_created_by}] = ?"
        params.append(created_by)
    elif created_by_username:
        where += f" AND [{col_created_by}] = ?"
        params.append(created_by_username)
    else:
        return stats

    try:
        req_rows = fetch_all(f"SELECT [{col_id}] AS req_id FROM [tblExperimentRequests] WHERE {where}", params)
    except Exception as e:
        stats["errors"].append(f"select draft requests: {e}")
        return stats

    request_ids = [r.get("req_id") for r in req_rows if isinstance(r, dict) and r.get("req_id") is not None]
    stats["requests_found"] = len(request_ids)
    if not request_ids:
        return stats

    # Images-Tabelle optional
    img_table_exists = False
    try:
        img_table_exists = table_exists("tblExperimentRequestImage")
    except Exception:
        img_table_exists = False

    img_cols: Dict[str, str] = {}
    col_fk = None
    col_rel = None
    if img_table_exists:
        try:
            img_cols = get_columns_map("tblExperimentRequestImage")
            # FK kann ExperimentRequestID oder RequestID heissen
            col_fk = (
                img_cols.get("experimentrequestid")
                or img_cols.get("requestid")
                or "ExperimentRequestID"
            )
            col_rel = img_cols.get("relativepath") or "RelativePath"
        except Exception as e:
            stats["errors"].append(f"get_columns_map(tblExperimentRequestImage): {e}")
            img_table_exists = False

    for rid in request_ids:
        rel_paths: list[str] = []

        if img_table_exists and col_fk and col_rel:
            try:
                img_rows = fetch_all(
                    f"SELECT [{col_rel}] AS rel FROM [tblExperimentRequestImage] WHERE [{col_fk}] = ?",
                    (rid,),
                )
                rel_paths = [str(r.get("rel")) for r in img_rows if isinstance(r, dict) and r.get("rel")]
            except Exception as e:
                stats["errors"].append(f"select images for request {rid}: {e}")

        # Folder löschen (distinct)
        for rp in sorted(set(rel_paths)):
            try:
                folder = os.path.normpath(rp)
                # Safety: nur Ordner löschen, keine Files
                if os.path.isdir(folder):
                    shutil.rmtree(folder, ignore_errors=False)
                    stats["folders_deleted"] += 1
            except FileNotFoundError:
                # Ordner existiert nicht → ok
                pass
            except Exception as e:
                stats["errors"].append(f"delete folder '{rp}' for request {rid}: {e}")

        # Image-rows löschen
        if img_table_exists and col_fk:
            try:
                stats["image_rows_deleted"] += execute(
                    f"DELETE FROM [tblExperimentRequestImage] WHERE [{col_fk}] = ?",
                    (rid,),
                )
            except Exception as e:
                stats["errors"].append(f"delete image rows for request {rid}: {e}")

        # Request löschen
        try:
            deleted = execute(f"DELETE FROM [tblExperimentRequests] WHERE [{col_id}] = ?", (rid,))
            stats["requests_deleted"] += int(deleted or 0)
        except Exception as e:
            stats["errors"].append(f"delete request {rid}: {e}")

    return stats

def get_user_id(username: str) -> Optional[int]:
    """
    Liefert die Primärschlüssel-ID (tblUser.ID) für den angegebenen Username.
    Gibt None zurück, wenn kein Treffer.
    """
    if not username:
        return None
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute("SELECT [ID] FROM tblUser WHERE [Username]=?", (username,))
        row = cur.fetchone()
        return int(row[0]) if row else None


def _canon_col(name: str) -> str:
    """Canonicalize column names for fuzzy matching."""
    return str(name or "").strip().strip("[]`").replace(" ", "").replace("_", "").lower()


def _resolve_field(cands: list[str], cols_map: dict[str, str]) -> Optional[str]:
    """Resolve a real column name from candidate names using get_columns_map()."""
    if not cols_map:
        return None
    canon2real = {_canon_col(k): v for k, v in cols_map.items()}
    for c in cands or []:
        key = _canon_col(c)
        if key in canon2real:
            return canon2real[key]
    # also try direct lower match (some maps use lower->real)
    for c in cands or []:
        low = str(c).strip().lower()
        if low in cols_map:
            return cols_map[low]
    return None


def get_user_first_last_name(username: str) -> tuple[str, str]:
    """Returns (FirstName, LastName) from tblUser for a given Username.

    Robust against naming variants (e.g. FirstName / "First Name" / Vorname).
    Returns ("", "") if not found.
    """
    if not username:
        return "", ""

    try:
        cols = get_columns_map("tblUser")
    except Exception:
        cols = {}

    col_first = _resolve_field(["FirstName", "First Name", "Vorname", "GivenName"], cols)
    col_last = _resolve_field(["LastName", "Last Name", "Nachname", "Surname", "FamilyName"], cols)

    if not (col_first or col_last):
        return "", ""

    sel = []
    sel.append(f"[{col_first}]" if col_first else "NULL")
    sel.append(f"[{col_last}]" if col_last else "NULL")
    sql = f"SELECT {', '.join(sel)} FROM tblUser WHERE [Username]=?"

    with get_connection() as cn:
        cur = cn.cursor()
        try:
            cur.execute(sql, (username,))
            row = cur.fetchone()
        except Exception:
            row = None

    if not row:
        return "", ""

    fn = "" if row[0] is None else str(row[0]).strip()
    ln = "" if row[1] is None else str(row[1]).strip()
    return fn, ln


def is_superuser(username: str) -> bool:
    """True, wenn tblUser.AccessLevel >= 4 für diesen User."""
    return get_user_access_level(username) >= 4


def update_trialseries_reviewed(series_id: int, reviewed: bool) -> int:
    """DEPRECATED (wird nicht mehr verwendet).

    Das Feld tblTrialSeries.Reviewed wird in der aktuellen Programmlogik nicht
    mehr genutzt. Diese Funktion bleibt als No-Op bestehen, damit alte Imports
    (falls irgendwo noch vorhanden) nicht brechen.

    Rückgabe: 0
    """
    # Absichtlich keine DB-Operation mehr.
    return 0

def get_user_accent_colour(username: str):
    """Gibt tblUser.AccentColour zurück (z.B. '#8a2be2') oder None."""
    if not username:
        return None
    with get_connection() as cn:
        cur = cn.cursor()
        try:
            cur.execute(
                "SELECT [AccentColour] FROM tblUser WHERE [Username]=?",
                (username,),
            )
            row = cur.fetchone()
        except Exception:
            return None
    if not row:
        return None
    val = row[0]
    if not val:
        return None
    return str(val).strip() or None