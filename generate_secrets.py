# generate_secrets.py
# Einmalig ausführen um secrets.enc zu generieren.
# Danach secrets.enc ins Projekt legen und in tripplet.spec einbinden.
#
# pip install cryptography
#
# Ausführen: python generate_secrets.py

from cryptography.fernet import Fernet
from pathlib import Path

key = Fernet.generate_key()          # 44 Bytes, URL-safe base64
Path('secrets.enc').write_bytes(key)

print(f"✅ secrets.enc generiert.")
print(f"   Key: {key.decode()}")
print()
print("Nächste Schritte:")
print("  1. secrets.enc neben main.py / tripplet.spec ablegen")
print("  2. In tripplet.spec unter datas eintragen:")
print("       datas=[('secrets.enc', '.'), ...]")
print("  3. secrets.enc NIE ins Git commiten!")
print()
print("Zum Testen (einmalig verschlüsseln):")
print(f"  from cryptography.fernet import Fernet")
print(f"  f = Fernet({key!r})")
print(f"  enc = f.encrypt(b'sk-ant-...')")
