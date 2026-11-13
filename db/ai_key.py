# db/ai_key.py
"""Personal Anthropic API key + monthly token quota (tblUser.api_key_enc,
token_limit, tokens_used, tokens_reset) - Qt-free, shared by Athena / Lab
Assistant / help search (desktop, via ui/advisor_worker.py) and the web app.
Moved unchanged from ui/advisor_worker.py 2026-11-13; reset_tokens_if_due()
moved from ui/screen_login.py (monthly reset at login)."""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path
from typing import Optional

from db.connection import fetch_all
import app_meta


def _load_master_key() -> Optional[bytes]:
    """Lädt den Fernet MASTER_KEY aus secrets.enc (eingebettet via PyInstaller oder lokal)."""
    candidates = [Path("secrets.enc")]
    if getattr(sys, "frozen", False):
        candidates.insert(0, Path(sys._MEIPASS) / "secrets.enc")
    else:
        candidates.append(Path(__file__).parent.parent / "secrets.enc")

    for p in candidates:
        if p.exists():
            try:
                key = p.read_bytes().strip()
                if len(key) == 44:
                    return key
            except Exception:
                pass
    return None


def load_api_key() -> Optional[str]:
    """Lädt und entschlüsselt den Anthropic API Key für den aktuell eingeloggten User."""
    try:
        from cryptography.fernet import Fernet

        master_key = _load_master_key()
        if master_key:
            username = app_meta.current_user.get("username", "")
            if username:
                rows = fetch_all(
                    "SELECT api_key_enc, token_limit, tokens_used "
                    "FROM tbluser WHERE Username = %s",
                    [username]
                )
                if rows and rows[0].get("api_key_enc"):
                    enc   = rows[0]["api_key_enc"]
                    limit = rows[0].get("token_limit") or 0
                    used  = rows[0].get("tokens_used") or 0
                    if limit > 0 and used >= limit:
                        return None  # Limit erreicht
                    f = Fernet(master_key)
                    return f.decrypt(enc.encode("utf-8")).decode("utf-8")
    except Exception:
        pass

    # Fallback: ai_secrets.json (Dev-Modus)
    for p in [Path("ai_secrets.json"), Path(r"C:\ProgramData\TrippleT\ai_secrets.json")]:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                key  = data.get("anthropic_api_key", "").strip()
                if key:
                    return key
            except Exception:
                pass
    return None


def update_token_usage(input_tokens: int, output_tokens: int) -> None:
    """Schreibt den Token-Verbrauch nach einem API-Call in tbluser zurück."""
    try:
        from db.connection import execute
        username = app_meta.current_user.get("username", "")
        if username:
            execute(
                "UPDATE tblUser SET tokens_used = tokens_used + %s WHERE Username = %s",
                [input_tokens + output_tokens, username]
            )
    except Exception:
        pass


def reset_tokens_if_due(username: str) -> Optional[bool]:
    """Monthly quota reset at login: tokens_used = 0 when tokens_reset is
    empty or not in the future (then the next reset is in one month).
    True = reset, False = still valid, None = failed (never blocks a login)."""
    try:
        from db.connection import execute as db_execute
        reset_rows = fetch_all("SELECT tokens_reset FROM tblUser WHERE Username = %s", [username])
        if reset_rows and reset_rows[0].get("tokens_reset"):
            last = reset_rows[0]["tokens_reset"]
            if isinstance(last, str):
                last = datetime.date.fromisoformat(last)
            if last > datetime.date.today():
                return False
        db_execute("UPDATE tblUser SET tokens_used = 0, tokens_reset = CURDATE() + INTERVAL 1 MONTH "
                   "WHERE Username = %s", [username])
        return True
    except Exception as e:
        print(f"Athena token reset failed: {e}", flush=True)
        return None
