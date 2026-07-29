"""
TrippleT – Stufe 5 Regressionstests mit echten Daten
======================================================
Basiert auf zwei realen Files:
  - 271_24_130426_1255.tdms  → DTY-Signal, analyze_series-Pipeline
  - 419.pdf                  → Statimat DS-Bericht, parse_statimat_pdf

Golden-Output-Werte wurden einmalig aus den echten Files berechnet und in
tests/fixtures/ gespeichert. Die Tests stellen sicher dass sich diese Werte
bei zukünftigen Refactorings nicht unbemerkt verschieben.

Toleranzen:
  - Knoten/m, Schwellwert: ±0.5% relativ (Algorithmus-Stabilität)
  - Zählwerte (knot_n, ABC): exakt (deterministisch)
  - Statistik-Felder:       ±1% relativ
  - PDF-Werte:              exakt (deterministischer Parser)

Voraussetzungen:
  pip install nptdms pdfplumber
  TDMS-File und PDF müssen in tests/fixtures/ liegen ODER der Pfad
  wird via Umgebungsvariable TTT_FIXTURE_DIR gesetzt.

Ausführen:
  cd TrippleT
  pytest tests/test_ttt_regression.py -v
"""

import sys
import os
import json
import math
import pytest

# Pfad-Setup (identisch zu test_ttt_ui.py)
def _find_ttt_root():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ttt"),
        os.getcwd(),
        "/home/claude/ttt/ttt",
    ]
    for c in candidates:
        c = os.path.abspath(c)
        if os.path.isdir(os.path.join(c, "ui")):
            return c
    raise RuntimeError("ttt/-Verzeichnis nicht gefunden.")

_TTT_ROOT = _find_ttt_root()
if _TTT_ROOT not in sys.path:
    sys.path.insert(0, _TTT_ROOT)

# Fixture-Verzeichnis: tests/fixtures/ neben dieser Datei,
# oder via Umgebungsvariable TTT_FIXTURE_DIR überschreibbar
_FIXTURE_DIR = os.environ.get(
    "TTT_FIXTURE_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures"),
)

_TDMS_FILE    = os.path.join(_FIXTURE_DIR, "271_24_130426_1255.tdms")
_PDF_FILE     = os.path.join(_FIXTURE_DIR, "419.pdf")
_GOLDEN_DTY   = os.path.join(_FIXTURE_DIR, "golden_dty_271_24.json")
_GOLDEN_STAT  = os.path.join(_FIXTURE_DIR, "golden_statimat_419.json")

# Marks: überspringen wenn Fixture-Files fehlen
needs_tdms = pytest.mark.skipif(
    not os.path.exists(_TDMS_FILE),
    reason=f"TDMS-File nicht gefunden: {_TDMS_FILE}",
)
needs_pdf = pytest.mark.skipif(
    not os.path.exists(_PDF_FILE),
    reason=f"PDF-File nicht gefunden: {_PDF_FILE}",
)


def _load_golden(path):
    with open(path) as f:
        return json.load(f)["golden"]


def _approx_rel(expected, tol=0.005):
    """Relative Toleranz: ±0.5% vom Erwartungswert."""
    return pytest.approx(expected, rel=tol)


# ===========================================================================
# DTY-Analyse: analyze_series auf echtem TDMS-Signal
# ===========================================================================

@pytest.fixture(scope="module")
def dty_result():
    """Lädt das TDMS-File einmal pro Test-Session und führt analyze_series aus."""
    import numpy as np
    from nptdms import TdmsFile
    from ui.yarnscope.dty_analysis import analyze_series

    f = TdmsFile.read(_TDMS_FILE)
    sig = f["Rohdaten"]["271_24 (x-Achse)"][:].astype(np.float64)
    res = analyze_series(sig, dx_mm=0.25, min_seg_pts=5)
    return res


@pytest.fixture(scope="module")
def dty_golden():
    return _load_golden(_GOLDEN_DTY)


class TestDtyAnalyzeSeriesRegression:
    """Regressionstests für analyze_series auf dem echten DTY-Signal 271_24."""

    @needs_tdms
    def test_signal_wird_geladen(self):
        """Prüft dass der TDMS-Channel korrekt geladen wird."""
        import numpy as np
        from nptdms import TdmsFile
        f = TdmsFile.read(_TDMS_FILE)
        sig = f["Rohdaten"]["271_24 (x-Achse)"][:].astype(np.float64)
        assert len(sig) == 400226
        assert abs(sig.mean() - 1489.4525) < 0.01
        assert abs(sig.std()  -   25.1772) < 0.01

    @needs_tdms
    def test_schwellwert_stabil(self, dty_result, dty_golden):
        """Otsu-Schwellwert darf sich bei Refactoring nicht verschieben."""
        assert dty_result["threshold"] == _approx_rel(dty_golden["threshold"])

    @needs_tdms
    def test_knoten_pro_meter_stabil(self, dty_result, dty_golden):
        """Knoten/m ist die wichtigste Kennzahl – muss exakt reproduzierbar sein."""
        assert dty_result["knots_per_m"] == _approx_rel(dty_golden["knots_per_m"])

    @needs_tdms
    def test_knoten_anzahl_exakt(self, dty_result, dty_golden):
        """Absolute Knotenanzahl ist deterministisch – muss exakt stimmen."""
        assert dty_result["knot"]["n"] == dty_golden["knot_n"]

    @needs_tdms
    def test_abc_counts_exakt(self, dty_result, dty_golden):
        """A/B/C-Klassifizierung ist deterministisch."""
        counts = dty_result["classes"]["counts"]
        assert counts["A"] == dty_golden["abc_A"]
        assert counts["B"] == dty_golden["abc_B"]
        assert counts["C"] == dty_golden["abc_C"]

    @needs_tdms
    def test_abc_summe_gleich_knoten_n(self, dty_result, dty_golden):
        """Summe A+B+C muss gleich Knoten-n sein."""
        counts = dty_result["classes"]["counts"]
        assert sum(counts.values()) == dty_golden["knot_n"]

    @needs_tdms
    def test_knot_mean_stabil(self, dty_result, dty_golden):
        """Mittlere Knotenlänge [mm] muss stabil bleiben."""
        assert dty_result["knot"]["mean"] == _approx_rel(dty_golden["knot_mean"])

    @needs_tdms
    def test_knot_cv_stabil(self, dty_result, dty_golden):
        """CV der Knotenlänge muss stabil bleiben."""
        assert dty_result["knot"]["cv"] == _approx_rel(dty_golden["knot_cv"], tol=0.01)

    @needs_tdms
    def test_open_mean_stabil(self, dty_result, dty_golden):
        """Mittlere Öffnungslänge [mm] muss stabil bleiben."""
        assert dty_result["open"]["mean"] == _approx_rel(dty_golden["open_mean"])

    @needs_tdms
    def test_open_cv_stabil(self, dty_result, dty_golden):
        assert dty_result["open"]["cv"] == _approx_rel(dty_golden["open_cv"], tol=0.01)

    @needs_tdms
    def test_rapport_cv_global_stabil(self, dty_result, dty_golden):
        assert dty_result["rapport_cv_global"] == _approx_rel(dty_golden["rapport_cv_global"], tol=0.01)

    @needs_tdms
    def test_rapport_cv_local_stabil(self, dty_result, dty_golden):
        assert dty_result["rapport_cv_local"] == _approx_rel(dty_golden["rapport_cv_local"], tol=0.01)

    @needs_tdms
    def test_skewness_kl_stabil(self, dty_result, dty_golden):
        assert dty_result["skew_kl"] == _approx_rel(dty_golden["skew_kl"], tol=0.02)

    @needs_tdms
    def test_skewness_ol_stabil(self, dty_result, dty_golden):
        assert dty_result["skew_ol"] == _approx_rel(dty_golden["skew_ol"], tol=0.05)

    @needs_tdms
    def test_autocorrelation_kl_stabil(self, dty_result, dty_golden):
        assert dty_result["kl_ac1"] == _approx_rel(dty_golden["kl_ac1"], tol=0.05)

    @needs_tdms
    def test_tail_ratio_stabil(self, dty_result, dty_golden):
        assert dty_result["kl_tail_ratio"] == _approx_rel(dty_golden["kl_tail_ratio"], tol=0.01)

    @needs_tdms
    def test_hysterese_grenzen_stabil(self, dty_result, dty_golden):
        assert dty_result["h_low"]  == _approx_rel(dty_golden["h_low"])
        assert dty_result["h_high"] == _approx_rel(dty_golden["h_high"])

    @needs_tdms
    def test_result_hat_alle_pflichtfelder(self, dty_result):
        """Stellt sicher dass analyze_series alle erwarteten Felder zurückgibt."""
        pflichtfelder = [
            "threshold", "h_low", "h_high",
            "knots_per_m", "knots_per_m_det", "knots_per_m_raw",
            "knot", "open", "rapport", "classes",
            "skew_kl", "skew_ol",
            "rapport_cv_global", "rapport_cv_local",
            "kl_ac1", "kl_ac2", "kl_ac3",
            "kl_tail_ratio", "ol_tail_ratio",
            "ka_oa_ratio", "kl_asym_mean",
            "kurt_kl", "kurt_ol",
            "thickness_drift",
        ]
        for f in pflichtfelder:
            assert f in dty_result, f"Pflichtfeld fehlt: {f!r}"

    @needs_tdms
    def test_alle_numerischen_felder_finite(self, dty_result):
        """Keine NaN/Inf in den Hauptkennzahlen."""
        for key in ["threshold", "knots_per_m", "knots_per_m_det"]:
            val = dty_result[key]
            assert val is not None and math.isfinite(val), \
                f"{key} = {val!r} ist nicht finit"

    @needs_tdms
    def test_knots_per_m_im_realistischen_bereich(self, dty_result):
        """Plausibilitätsprüfung: DTY-Garn hat typisch 50–300 Knoten/m."""
        assert 50 < dty_result["knots_per_m"] < 300

    @needs_tdms
    def test_manueller_schwellwert_ueberschreibt_otsu(self):
        """Wenn manual_T gesetzt, muss dieser exakt verwendet werden."""
        import numpy as np
        from nptdms import TdmsFile
        from ui.yarnscope.dty_analysis import analyze_series

        f = TdmsFile.read(_TDMS_FILE)
        sig = f["Rohdaten"]["271_24 (x-Achse)"][:].astype(np.float64)
        manual_T = 1490.0
        res = analyze_series(sig, dx_mm=0.25, min_seg_pts=5, manual_T=manual_T)
        assert res["threshold"] == pytest.approx(manual_T)


# ===========================================================================
# Statimat-PDF: parse_statimat_pdf auf echtem Bericht
# ===========================================================================

@pytest.fixture(scope="module")
def statimat_result():
    from ui.widgets.statimat_pdf_parser import parse_statimat_pdf
    return parse_statimat_pdf(_PDF_FILE)


@pytest.fixture(scope="module")
def statimat_golden():
    return _load_golden(_GOLDEN_STAT)


class TestStatimatPdfRegression:
    """Regressionstests für parse_statimat_pdf auf dem echten Statimat-DS-Bericht."""

    @needs_pdf
    def test_header_customer_korrekt(self, statimat_result, statimat_golden):
        header, _ = statimat_result
        assert header["customer"] == statimat_golden["header_customer"]

    @needs_pdf
    def test_header_material_korrekt(self, statimat_result, statimat_golden):
        header, _ = statimat_result
        assert header["material"] == statimat_golden["header_material"]

    @needs_pdf
    def test_header_device_korrekt(self, statimat_result, statimat_golden):
        header, _ = statimat_result
        assert header["device"] == statimat_golden["header_device"]

    @needs_pdf
    def test_anzahl_records_korrekt(self, statimat_result, statimat_golden):
        _, records = statimat_result
        assert len(records) == statimat_golden["n_records"]

    @needs_pdf
    def test_spulennummer_korrekt(self, statimat_result, statimat_golden):
        _, records = statimat_result
        assert records[0]["spool_no"] == statimat_golden["spool_no"]

    @needs_pdf
    def test_feinheit_korrekt(self, statimat_result, statimat_golden):
        _, records = statimat_result
        assert records[0]["feinheit_x"] == pytest.approx(statimat_golden["feinheit_x"])

    @needs_pdf
    def test_dehnung_mean_korrekt(self, statimat_result, statimat_golden):
        _, records = statimat_result
        assert records[0]["dehnung_x"] == pytest.approx(statimat_golden["dehnung_x"])

    @needs_pdf
    def test_dehnung_cv_korrekt(self, statimat_result, statimat_golden):
        _, records = statimat_result
        assert records[0]["dehnung_cv"] == pytest.approx(statimat_golden["dehnung_cv"])

    @needs_pdf
    def test_festigkeit_mean_korrekt(self, statimat_result, statimat_golden):
        _, records = statimat_result
        assert records[0]["festigkeit_x"] == pytest.approx(statimat_golden["festigkeit_x"])

    @needs_pdf
    def test_festigkeit_cv_korrekt(self, statimat_result, statimat_golden):
        _, records = statimat_result
        assert records[0]["festigkeit_cv"] == pytest.approx(statimat_golden["festigkeit_cv"])

    @needs_pdf
    def test_record_hat_alle_pflichtfelder(self, statimat_result):
        _, records = statimat_result
        for key in ["page", "spool_no", "feinheit_x",
                    "dehnung_x", "dehnung_cv",
                    "festigkeit_x", "festigkeit_cv"]:
            assert key in records[0], f"Pflichtfeld fehlt: {key!r}"

    @needs_pdf
    def test_keine_none_werte_in_hauptfeldern(self, statimat_result):
        """Für diesen bekannten Bericht dürfen keine Felder None sein."""
        _, records = statimat_result
        r = records[0]
        for key in ["feinheit_x", "dehnung_x", "dehnung_cv",
                    "festigkeit_x", "festigkeit_cv"]:
            assert r[key] is not None, f"{key} ist None"

    @needs_pdf
    def test_feinheit_im_plausiblen_bereich(self, statimat_result):
        """Feinheit von PES 110f36 muss im realistischen Bereich liegen."""
        _, records = statimat_result
        feinheit = records[0]["feinheit_x"]
        assert 90 < feinheit < 130, f"Feinheit {feinheit} ausserhalb 90–130 dtex"

    @needs_pdf
    def test_festigkeit_im_plausiblen_bereich(self, statimat_result):
        """Festigkeit für PES muss typisch 3–6 cN/dtex sein."""
        _, records = statimat_result
        fest = records[0]["festigkeit_x"]
        assert 2.0 < fest < 7.0, f"Festigkeit {fest} ausserhalb 2–7 cN/dtex"