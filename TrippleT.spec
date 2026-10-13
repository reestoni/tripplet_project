# TrippleT.spec — PyInstaller build script (Windows, onedir)
# Fixes MySQL auth plugin runtime error (2059) by bundling mysql namespace + connector plugins.
#
# Build:
#   cd C:\python\TrippleT_project
#   .\.venv\Scripts\activate
#   python -m PyInstaller TrippleT.spec --clean --noconfirm

from PyInstaller.utils.hooks import (
    collect_all,
    collect_submodules,
    collect_data_files,
)
import os, sys

# --- PySide6 (Qt plugins etc.)
pyside6_datas, pyside6_binaries, pyside6_hidden = collect_all("PySide6")

# --- pyodbc
pyodbc_datas, pyodbc_binaries, pyodbc_hidden = collect_all("pyodbc")

# --- mysql-connector-python
# mysql-connector-python lives under the namespace package "mysql".
# The connector loads auth plugins dynamically (mysql.connector.plugins.*),
# which PyInstaller won't detect unless we include them explicitly.
mysql_datas = collect_data_files("mysql")
mysql_hidden = collect_submodules("mysql")  # includes mysql.connector + mysql.connector.plugins.*

# (Optional but harmless) include connector package binaries/datas as well
mysqlc_datas, mysqlc_binaries, mysqlc_hidden = collect_all("mysql.connector")
mysql_datas += mysqlc_datas
mysql_hidden += mysqlc_hidden

# --- ddddocr (OCR for Itemat PDF import)
# ddddocr ships an ONNX model file that must be bundled explicitly.
ddddocr_datas, ddddocr_binaries, ddddocr_hidden = collect_all("ddddocr")

# --- onnxruntime (runtime backend for ddddocr)
ort_datas, ort_binaries, ort_hidden = collect_all("onnxruntime")

# --- PyMuPDF / fitz (PDF rendering for Itemat + Statimat)
fitz_datas, fitz_binaries, fitz_hidden = collect_all("fitz")
pymupdf_datas, pymupdf_binaries, pymupdf_hidden = collect_all("pymupdf")

# --- pdfplumber (text extraction for Statimat PDFs)
pdfplumber_datas, pdfplumber_binaries, pdfplumber_hidden = collect_all("pdfplumber")
pdfminer_datas, pdfminer_binaries, pdfminer_hidden = collect_all("pdfminer")  # pdfplumber dependency

# --- ML-Stack (YarnScope Stabilitäts-Predictions)
# joblib, pandas, xgboost, lightgbm, sklearn werden in dty_analysis.py dynamisch
# importiert — PyInstaller erkennt sie ohne explizite collect_all()-Eintraege nicht.
joblib_datas,  joblib_binaries,  joblib_hidden  = collect_all("joblib")
pandas_datas,  pandas_binaries,  pandas_hidden  = collect_all("pandas")
xgboost_datas, xgboost_binaries, xgboost_hidden = collect_all("xgboost")
sklearn_datas, sklearn_binaries, sklearn_hidden  = collect_all("sklearn")
# lightgbm: stab_10.joblib enthaelt einen LGBMRegressor
try:
    lgbm_datas, lgbm_binaries, lgbm_hidden = collect_all("lightgbm")
except Exception:
    lgbm_datas, lgbm_binaries, lgbm_hidden = [], [], []

# --- cryptography (Fernet encryption fuer API Keys in tbluser)
cryptography_datas, cryptography_binaries, cryptography_hidden = collect_all("cryptography")

# --- anthropic (offizielles Claude-SDK, Hilfe-Suche "Ask AI", ui/widgets/help_ai.py)
# Laedt Teile (Ressourcen, httpx2-Transport, pydantic-Modelle) dynamisch -> collect_all.
anthropic_datas, anthropic_binaries, anthropic_hidden = collect_all("anthropic")

# --- scipy
# scipy laedt einige Untermodule (u.a. scipy.*.array_api_compat.numpy.fft) dynamisch
# zur Laufzeit -- PyInstaller erkennt das nicht ueber einzelne hiddenimports.
# collect_all() wie bei den anderen ML-Paketen vermeidet "No module named ..."-Crashes.
scipy_datas, scipy_binaries, scipy_hidden = collect_all("scipy")

# Project assets (copied next to the EXE in onedir)
project_assets = [
    ("assets", "assets"),
    ("ui/yarnscope/garngraf_canvas.py", "ui/yarnscope"),
    ("secrets.enc", "."),                          # Fernet Master Key
    ("db_secrets.enc", "."),                       # DB-Credentials (Fernet-verschlüsselt)
    ("assets/owl_sprites", "assets/owl_sprites"),  # Athena Eulen-Sprites
]

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=(
        pyside6_binaries + pyodbc_binaries + mysqlc_binaries
        + ddddocr_binaries + ort_binaries
        + fitz_binaries + pymupdf_binaries
        + pdfplumber_binaries + pdfminer_binaries
        + cryptography_binaries
        + joblib_binaries + pandas_binaries + xgboost_binaries
        + sklearn_binaries + lgbm_binaries
        + scipy_binaries
        + anthropic_binaries
    ),
    datas=(
        pyside6_datas + pyodbc_datas + mysql_datas + project_assets
        + ddddocr_datas + ort_datas
        + fitz_datas + pymupdf_datas
        + pdfplumber_datas + pdfminer_datas
        + cryptography_datas
        + joblib_datas + pandas_datas + xgboost_datas
        + sklearn_datas + lgbm_datas
        + scipy_datas
        + anthropic_datas
    ),
    hiddenimports=(
        pyside6_hidden + pyodbc_hidden + mysql_hidden
        + ddddocr_hidden + ort_hidden
        + fitz_hidden + pymupdf_hidden
        + pdfplumber_hidden + pdfminer_hidden
        + cryptography_hidden
        + scipy_hidden
        + anthropic_hidden
        + [
            # onnxruntime loads its C-extension dynamically — must be explicit
            "onnxruntime.capi._pybind_state",
            # ddddocr uses these at runtime
            "ddddocr",
            "numpy",
            "PIL",
            "PIL.Image",
            "PIL.ImageEnhance",
            "PIL.ImageFilter",
            "PIL.ImageOps",
            # matplotlib (used in yarnscope garngraf)
            "matplotlib",
            "matplotlib.pyplot",
            "matplotlib.backends.backend_qtagg",
            # ── TrippleT project modules ──────────────────────────────────
            # ATY + DTY Batch-Screens (lazy import via _aty_open_batch / _ys_open_batch)
            "ui.screen_aty_batch",
            "ui.screen_tdms_batch",
            # YarnScope Analyse-Module (lazy import in screen_show_experiment + batch)
            "ui.yarnscope.dty_analysis",
            "ui.yarnscope.dty_tdms_reader",
            "ui.yarnscope.garngraf_canvas",
            "ui.yarnscope.aty_canvas",
            # ATY Dickstellen-Analyse (lazy import in aty_yarnscope_tab + screen_aty_batch)
            "thick_spot_analysis",
            # Weitere lazy-importierte UI-Module
            "ui.screen_create_experiment_request",
            "ui.yarnscope.garngraf",
            # agentT – Advisor Worker
            "ui.advisor_worker",
            # ML-Stack fuer YarnScope Stabilitaets-Predictions
            "joblib",
            "pandas",
            "pandas._libs.tslibs.np_datetime",
            "pandas._libs.tslibs.nattype",
            "pandas._libs.tslibs.timezones",
            "xgboost",
            "xgboost.sklearn",
            "lightgbm",
            "lightgbm.sklearn",
            "sklearn",
            "sklearn.utils._cython_blas",
            "sklearn.neighbors._partition_nodes",
            "scipy",
            "scipy.special._cython_special",
            # cryptography – Fernet für API Key Verschlüsselung
            "cryptography",
            "cryptography.fernet",
            "cryptography.hazmat.primitives.ciphers",
            "cryptography.hazmat.backends",
        ]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="TrippleT",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,  # GUI app
    icon="assets/icons/t3_logo_mini.ico",
)

# ONEDIR build (recommended for Qt apps)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TrippleT",
)

# db_secrets.enc ist via project_assets bereits ins Bundle eingebettet.
# Kein manuelles Kopieren nach dem Build nötig.
