"""encrypt_db_secrets.py
Einmaliges Hilfsskript: verschlüsselt db_secrets.json → db_secrets.enc
mit dem bestehenden Fernet Master-Key aus secrets.enc.

Ausführen (einmalig, im Projektordner):
    python encrypt_db_secrets.py

Danach kann db_secrets.json aus dem Projektordner entfernt oder in .gitignore
eingetragen werden. db_secrets.enc wird ins PyInstaller-Bundle eingebettet.
"""

import sys
from pathlib import Path


def main() -> None:
    # ── secrets.enc laden ────────────────────────────────────────────────────
    key_path = Path("secrets.enc")
    if not key_path.exists():
        print(f"[FEHLER] {key_path.resolve()} nicht gefunden.")
        sys.exit(1)

    master_key = key_path.read_bytes().strip()
    if len(master_key) != 44:
        print(f"[FEHLER] secrets.enc hat unerwartete Länge {len(master_key)} (erwartet: 44 Bytes).")
        sys.exit(1)

    # ── db_secrets.json laden ────────────────────────────────────────────────
    src = Path("db_secrets.json")
    if not src.exists():
        print(f"[FEHLER] {src.resolve()} nicht gefunden.")
        sys.exit(1)

    plaintext = src.read_bytes()

    # ── verschlüsseln ────────────────────────────────────────────────────────
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        print("[FEHLER] 'cryptography' nicht installiert. pip install cryptography")
        sys.exit(1)

    f = Fernet(master_key)
    ciphertext = f.encrypt(plaintext)

    # ── db_secrets.enc schreiben ─────────────────────────────────────────────
    dst = Path("db_secrets.enc")
    dst.write_bytes(ciphertext)
    print(f"[OK] {src} → {dst}  ({len(ciphertext)} Bytes)")
    print()
    print("Nächste Schritte:")
    print("  1. db_secrets.enc ist ab jetzt die Quelle – in .gitignore aufnehmen, falls gewünscht")
    print("  2. db_secrets.json kann aus dem dist-Ordner entfernt werden")
    print("  3. TrippleT.spec und connection.py verwenden ab jetzt db_secrets.enc automatisch")


if __name__ == "__main__":
    main()