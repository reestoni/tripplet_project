
@echo on
REM build_tripplet_verbose.bat — Robust one-click build for TrippleT (Windows)
REM Double-click me in Explorer from the project root (same folder as main.py).

setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

REM ---- Sanity checks ----
if not exist "main.py" (
  echo [ERROR] Diese Datei muss im gleichen Ordner liegen wie main.py
  echo Aktueller Ordner: %cd%
  pause
  exit /b 1
)

if not exist "assets" (
  echo [WARN] assets\-Ordner fehlt. Icons/Bilder werden dann nicht gebundled.
)

REM ---- Find Python launcher (py) or python ----
set PYCMD=
where py >nul 2>&1 && set PYCMD=py
if "%PYCMD%"=="" where python >nul 2>&1 && set PYCMD=python

if "%PYCMD%"=="" (
  echo [ERROR] Python wurde nicht gefunden. Bitte Python 3.10–3.12 (64-bit) installieren.
  pause
  exit /b 1
)

REM ---- Create and activate venv (.venv) ----
%PYCMD% -m venv .venv
if errorlevel 1 (
  echo [INFO] venv existiert evtl. bereits. Wir nutzen sie.
)

if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Virtuelle Umgebung konnte nicht erstellt werden (.venv fehlt).
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"

REM ---- Upgrade pip and install deps ----
python -m pip install --upgrade pip
if errorlevel 1 goto :pip_fail

python -m pip install pyinstaller PySide6 pyodbc
if errorlevel 1 goto :pip_fail

REM ---- Build: prefer spec, else fallback CLI ----
if exist "TrippleT.spec" (
  python -m PyInstaller TrippleT.spec --clean --noconfirm
) else (
  echo [INFO] Keine TrippleT.spec gefunden – baue mit Fallback-Parametern.
  python -m PyInstaller main.py --name TrippleT --clean --noconfirm --windowed ^
    --icon assets\icons\t3_logo_mini.ico ^
    --hidden-import pyodbc ^
    --collect-all PySide6 ^
    --add-data "assets;assets"
)

if errorlevel 1 goto :build_fail

echo.
echo [OK] Build fertig: .\dist\TrippleT\TrippleT.exe
echo.
pause
exit /b 0

:pip_fail
echo [ERROR] Python-Abhaengigkeiten konnten nicht installiert werden.
echo         Bitte pruefe Internetzugang/Proxy oder fuehre das Skript mit Admin-Rechten aus.
pause
exit /b 1

:build_fail
echo [ERROR] PyInstaller Build fehlgeschlagen.
echo         Siehe Ausgabe oben fuer Details.
pause
exit /b 1
