
@echo off
REM build_tripplet.bat — Double-click me from Explorer to build TrippleT.exe

REM Always run from the folder where this .bat lives
cd /d "%~dp0"

REM Sanity check: must be the project root (where main.py is)
if not exist "main.py" (
  echo.
  echo [Fehler] Diese Datei muss im Projekt-Ordner liegen (wo main.py ist).
  echo Aktueller Ordner: %cd%
  echo.
  pause
  exit /b 1
)

echo === TrippleT Build startet ===
echo Python/Tools installieren (falls noetig)...
echo.

REM Use the "py" launcher if available (standard on Windows)
where py >nul 2>&1
if %errorlevel%==0 (
  py -m pip install --upgrade pip
  py -m pip install pyinstaller PySide6 pyodbc
  py -m PyInstaller TrippleT.spec --clean --noconfirm
) else (
  REM Fallback: try python on PATH
  python -m pip install --upgrade pip
  python -m pip install pyinstaller PySide6 pyodbc
  python -m PyInstaller TrippleT.spec --clean --noconfirm
)

echo.
echo === Build fertig ===
echo Output: .\dist\TrippleT\TrippleT.exe
echo.
pause
