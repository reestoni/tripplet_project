
TrippleT — Windows Build Guide (PyInstaller)
===========================================

Prereqs
-------
1) Use **Python 3.10–3.12 (64-bit)**.
2) Install **Microsoft Access Database Engine 2016 (x64)** on the target
   machine so the ODBC driver
   {Microsoft Access Driver (*.mdb, *.accdb)}
   is available. The bitness **must match** Python (64-bit ↔ 64-bit).
3) Make sure your project layout contains:
   - main.py (entry point)
   - assets/ (images, icons, etc.) — e.g. assets/icons/t3_logo_mini.ico
   - ui/, db/, etc. as Python packages

Build (recommended: onedir)
---------------------------
1) Open a terminal **in the project root** (where main.py lives).
2) Copy TrippleT.spec and build_tripplet.bat into that folder.
3) Run:
   build_tripplet.bat

The result is at:  dist/TrippleT/TrippleT.exe

Notes / Troubleshooting
-----------------------
- If you see a blank window or missing icons, ensure the **assets/** folder
  exists and is deployed next to the EXE (the spec bundles it).
- If pyodbc raises "data source name not found", install the **Access
  Database Engine** matching your Python bitness (x64 recommended).
- Antivirus false positives can happen with unsigned EXEs. Consider **code
  signing** for distribution.
- Onefile build is possible (add --onefile to the pyinstaller command or
  adapt the spec), but startup is slower. Onedir is smoother for Qt apps.
- If you relocated the .accdb to a network share, verify permissions and
  that the path is reachable from the target machine. Your connection.py
  already tries ENV -> network -> local fallback.
