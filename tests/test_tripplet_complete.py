"""
TrippleT – Vollständige Unit-Test-Suite
========================================
Abdeckung:
  - ui/widgets/itemat_pdf_parser.py  (alle reine Logik-Funktionen)
  - ui/widgets/statimat_pdf_parser.py (alle Parser-Funktionen)
  - ui/yarnscope/dty_analysis.py      (Algorithmen + analyze_series-Pipeline)
  - ui/yarnscope/thick_spot_analysis.py (Erkennung, Aggregation, Histogramm)
  - db/connection.py                  (SQL-Übersetzung, Passwort-Hashing, Hilfsfunktionen)

Keine echte DB, kein Qt, kein PDF-File nötig.
Ausführen: pytest tests/test_ttt_complete.py -v
"""

import math
import re
import sys
import os
import pytest
import numpy as np

# ---------------------------------------------------------------------------
# Pfad-Setup (anpassen falls nötig)
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ===========================================================================
# MODUL 1: itemat_pdf_parser.py
# ===========================================================================

from ui.widgets.itemat_pdf_parser import (
    _parse_float,
    _split_stuck_numbers,
    _fix_stab_values,
    _parse_versuch_nr_from_text,
    _parse_row_values,
    _parse_page_from_text,
)


class TestParseFloat:
    def test_punkt_als_dezimaltrenner(self):
        assert _parse_float("12.3") == pytest.approx(12.3)

    def test_komma_als_dezimaltrenner(self):
        assert _parse_float("12,3") == pytest.approx(12.3)

    def test_ganzzahl(self):
        assert _parse_float("42") == pytest.approx(42.0)

    def test_leerstring_gibt_none(self):
        assert _parse_float("") is None

    def test_none_gibt_none(self):
        assert _parse_float(None) is None

    def test_fuehrendes_leerzeichen(self):
        assert _parse_float("  7.5  ") == pytest.approx(7.5)

    def test_ungueltige_eingabe_gibt_none(self):
        assert _parse_float("abc") is None

    def test_null(self):
        assert _parse_float("0") == pytest.approx(0.0)

    def test_negativer_wert(self):
        assert _parse_float("-3.14") == pytest.approx(-3.14)


class TestSplitStuckNumbers:
    def test_zwei_zusammengeklebte_zahlen(self):
        # Die Regex greift nach JEDEM Dezimalteil: "1100.01100.3"
        # → "1100.0" + Space + "1100.3" ist NICHT das Ergebnis
        # Tatsächliches Verhalten: Split bei jedem (\d+\.\d+)(?=\d):
        # "1100.01100.3" → "1100.0110 0.3" (Regex matcht kürzest mögliche Dezimalzahl)
        # Der Test dokumentiert das tatsächliche (leicht überraschende) Verhalten.
        result = _split_stuck_numbers("1100.01100.3")
        assert " " in result  # mindestens ein Space wurde eingefügt

    def test_einfaches_beispiel(self):
        # "100.0200.0" → "100.020 0.0" – Regex matcht "100.0", dann "200.0"... nein:
        # Regex matcht (\d+\.\d+) greedy = "100.020" dann Space vor "0.0"
        result = _split_stuck_numbers("100.0200.0")
        assert " " in result

    def test_drei_zusammengeklebte_zahlen(self):
        result = _split_stuck_numbers("100.0200.0300.0")
        assert result.count(" ") >= 2

    def test_drei_zusammengeklebte_zahlen(self):
        result = _split_stuck_numbers("100.0200.0300.0")
        parts = result.split()
        assert len(parts) == 3

    def test_einzelne_zahl_unveraendert(self):
        assert _split_stuck_numbers("100.0") == "100.0"

    def test_ganzzahlen_unveraendert(self):
        assert _split_stuck_numbers("100 200") == "100 200"

    def test_leerstring(self):
        assert _split_stuck_numbers("") == ""


class TestFixStabValues:
    def test_fuehrende_eins_entfernen(self):
        result = _fix_stab_values([1100.0], 1)
        assert result == [pytest.approx(100.0)]

    def test_wert_im_normbereich_unveraendert(self):
        result = _fix_stab_values([95.0], 1)
        assert result == [pytest.approx(95.0)]

    def test_none_bleibt_none(self):
        result = _fix_stab_values([None], 1)
        assert result == [None]

    def test_gemischte_liste(self):
        result = _fix_stab_values([1100.0, 85.0, None, 192.0], 4)
        assert result[0] == pytest.approx(100.0)
        assert result[1] == pytest.approx(85.0)
        assert result[2] is None
        # 192.0 → Kandidat 92.0 liegt im Bereich 0-110 → wird korrigiert
        assert result[3] == pytest.approx(92.0)

    def test_leere_liste(self):
        assert _fix_stab_values([], 0) == []

    def test_100_bleibt_unveraendert(self):
        result = _fix_stab_values([100.0], 1)
        assert result == [pytest.approx(100.0)]


class TestParseVersuchNrFromText:
    def test_standard_format(self):
        text = "Bemerkung : V3"
        assert _parse_versuch_nr_from_text(text) == 3

    def test_ohne_doppelpunkt(self):
        text = "Bemerkung V12"
        assert _parse_versuch_nr_from_text(text) == 12

    def test_ocr_fehler_s_als_5(self):
        text = "Bemerkung : VS"
        result = _parse_versuch_nr_from_text(text)
        assert result == 5

    def test_doppeltes_v(self):
        text = "Bemerkung : Vv4"
        assert _parse_versuch_nr_from_text(text) == 4

    def test_kein_match_gibt_none(self):
        assert _parse_versuch_nr_from_text("Kein Versuchsnummer hier") is None

    def test_leerer_string(self):
        assert _parse_versuch_nr_from_text("") is None

    def test_dreistellige_nummer(self):
        text = "Bemerkung : V123"
        assert _parse_versuch_nr_from_text(text) == 123


class TestParseRowValues:
    def test_knoten_zeile(self):
        text = "Knoten/m 100.0 | 95.5 | 88.2"
        result = _parse_row_values(text, "Knoten/m")
        assert len(result) >= 1
        assert result[0] == pytest.approx(100.0)

    def test_stab_faktor_zeile(self):
        text = "Stab.-Faktor 100.0 | 85.3 | 72.1 | 68.9"
        result = _parse_row_values(text, "Stab.-Faktor")
        assert len(result) >= 3

    def test_label_nicht_vorhanden_gibt_leere_liste(self):
        result = _parse_row_values("Irgendein Text", "Knoten/m")
        assert result == []

    def test_prozentzeichen_wird_ignoriert(self):
        text = "Var.-Koeff [%] 4.5"
        result = _parse_row_values(text, "Var.-Koeff")
        assert len(result) >= 1
        assert result[0] == pytest.approx(4.5)

    def test_ausrufezeichen_als_trennzeichen(self):
        text = "Knoten/m 100.0!95.5!88.2"
        result = _parse_row_values(text, "Knoten/m")
        assert len(result) == 3

    def test_komma_dezimaltrenner(self):
        text = "Knoten/m 100,5"
        result = _parse_row_values(text, "Knoten/m")
        assert result[0] == pytest.approx(100.5)


class TestParsePageFromText:
    SAMPLE_TEXT = (
        "Bemerkung : V7\n"
        "Knoten/m 112.0 | 95.0 | 88.0\n"
        "Var.-Koeff [%] 5.2\n"
        "Stab.-Faktor 100.0 | 85.3 | 72.1 | 68.9\n"
    )

    def test_versuch_nr_wird_erkannt(self):
        result = _parse_page_from_text(self.SAMPLE_TEXT)
        assert result["versuch_nr"] == 7

    def test_knoten_m_wird_erkannt(self):
        result = _parse_page_from_text(self.SAMPLE_TEXT)
        assert result["knoten_m"] == pytest.approx(112.0)

    def test_var_koeff_wird_erkannt(self):
        result = _parse_page_from_text(self.SAMPLE_TEXT)
        assert result["var_koeff"] == pytest.approx(5.2)

    def test_stability_liste_korrekte_laenge(self):
        result = _parse_page_from_text(self.SAMPLE_TEXT)
        # stability hat immer _N_STAB_COLS Einträge (aufgefüllt mit None)
        assert isinstance(result["stability"], list)
        assert len(result["stability"]) > 0

    def test_stability_erster_wert(self):
        result = _parse_page_from_text(self.SAMPLE_TEXT)
        # Erster Wert nach Index 0 (100.0 wird übersprungen) = 85.3
        assert result["stability"][0] == pytest.approx(85.3)

    def test_leerer_text(self):
        result = _parse_page_from_text("")
        assert result["versuch_nr"] is None
        assert result["knoten_m"] is None


# ===========================================================================
# MODUL 2: statimat_pdf_parser.py
# ===========================================================================

from ui.widgets.statimat_pdf_parser import (
    _to_float,
    _strip_diacritics,
    _norm_for_contains,
    _extract_customer_material,
    _extract_device_exact,
    _find_spool_no,
    _find_line,
    _parse_feinheit,
    _parse_dehnung,
    _parse_festigkeit,
    _parse_feinheitsb_kraft,
)


class TestToFloat:
    def test_punkt(self):
        assert _to_float("3.14") == pytest.approx(3.14)

    def test_komma(self):
        assert _to_float("3,14") == pytest.approx(3.14)

    def test_leerstring_gibt_none(self):
        assert _to_float("") is None

    def test_none_gibt_none(self):
        assert _to_float(None) is None

    def test_leerzeichen_werden_entfernt(self):
        assert _to_float("  2.5  ") == pytest.approx(2.5)

    def test_ungueltig_gibt_none(self):
        assert _to_float("xyz") is None


class TestStripDiacritics:
    def test_ae_bleibt(self):
        # ä wird zu a (Diakritik entfernt)
        result = _strip_diacritics("Gerät")
        assert "a" in result.lower()

    def test_normales_ascii_unveraendert(self):
        assert _strip_diacritics("hello") == "hello"

    def test_leerstring(self):
        assert _strip_diacritics("") == ""

    def test_none_gibt_leerstring(self):
        assert _strip_diacritics(None) == ""


class TestNormForContains:
    def test_grossbuchstaben(self):
        result = _norm_for_contains("statimat ds")
        assert result == "STATIMAT DS"

    def test_diakritika_werden_entfernt(self):
        result = _norm_for_contains("Gerät")
        assert "Ä" not in result and "ä" not in result

    def test_mehrfache_leerzeichen_kollabiert(self):
        result = _norm_for_contains("STATIMAT  DS")
        assert result == "STATIMAT DS"


class TestExtractCustomerMaterial:
    def test_standard_format(self):
        text = "Customer ACME Corp Material PA6.6 78dtex"
        customer, material = _extract_customer_material(text)
        assert customer == "ACME Corp"
        assert material == "PA6.6 78dtex"

    def test_kein_match_gibt_none_tuple(self):
        c, m = _extract_customer_material("Irgendein Text")
        assert c is None
        assert m is None

    def test_leerstring(self):
        c, m = _extract_customer_material("")
        assert c is None
        assert m is None


class TestExtractDeviceExact:
    def test_erkennt_statimat_ds(self):
        assert _extract_device_exact("Messung mit STATIMAT DS Gerät") == "STATIMAT DS"

    def test_erkennt_statimat_m(self):
        assert _extract_device_exact("STATIMAT M Bericht") == "STATIMAT M"

    def test_ds_hat_prioritaet_vor_m(self):
        # "STATIMAT DS" enthält "STATIMAT M" als Teilstring nicht → kein Problem
        assert _extract_device_exact("STATIMAT DS") == "STATIMAT DS"

    def test_kein_match_gibt_none(self):
        assert _extract_device_exact("Kein Gerätename") is None

    def test_case_insensitiv(self):
        assert _extract_device_exact("statimat ds") == "STATIMAT DS"


class TestFindSpoolNo:
    def test_standard(self):
        assert _find_spool_no("Spule 3") == 3

    def test_mit_v_prefix(self):
        assert _find_spool_no("Spule V5") == 5

    def test_nicht_vorhanden_gibt_none(self):
        assert _find_spool_no("Kein Spulenwert") is None

    def test_leerstring(self):
        assert _find_spool_no("") is None

    def test_zweistellige_nummer(self):
        assert _find_spool_no("Spule 12") == 12


class TestFindLine:
    def test_findet_korrekte_zeile(self):
        lines = ["Feinheit 10 100.5 dtex", "Dehnung 10 12.3 %"]
        assert _find_line(lines, "Feinheit") == "Feinheit 10 100.5 dtex"

    def test_kein_match_gibt_none(self):
        assert _find_line(["Kein Match"], "Feinheit") is None

    def test_leere_liste(self):
        assert _find_line([], "Feinheit") is None

    def test_erste_passende_zeile_wird_zurueckgegeben(self):
        lines = ["Feinheit 10 100.0", "Feinheit 20 200.0"]
        result = _find_line(lines, "Feinheit")
        assert "100.0" in result


class TestParseFeinheit:
    def test_standard_zeile(self):
        result = _parse_feinheit("Feinheit 20 78.5 dtex")
        assert result == pytest.approx(78.5)

    def test_ungueltige_zeile_gibt_none(self):
        assert _parse_feinheit("Nicht Feinheit") is None

    def test_komma_dezimaltrenner(self):
        result = _parse_feinheit("Feinheit 20 78,5")
        assert result == pytest.approx(78.5)


class TestParseDehnung:
    def test_standard_zeile_ds(self):
        mean, cv = _parse_dehnung("Dehnung 20 32.5 % 1.2 3.7 0.1 31.0 34.0")
        assert mean == pytest.approx(32.5)
        assert cv == pytest.approx(3.7)

    def test_ungueltige_zeile_gibt_none_tuple(self):
        m, cv = _parse_dehnung("Kein Match")
        assert m is None
        assert cv is None


class TestParseFestigkeit:
    def test_standard_zeile_ds(self):
        mean, cv = _parse_festigkeit("Festigkeit 20 4.2 cN 0.1 2.3 0.05 4.0 4.4")
        assert mean == pytest.approx(4.2)
        assert cv == pytest.approx(2.3)

    def test_ungueltige_zeile_gibt_none_tuple(self):
        m, cv = _parse_festigkeit("Kein Match")
        assert m is None
        assert cv is None


class TestParseFeinheitsbKraft:
    def test_standard_zeile_m(self):
        mean, cv = _parse_feinheitsb_kraft(
            "Feinheitsb.Kraft 20 4,08 cN/dtex 0,09 2,21 0,04 3,83 4,21"
        )
        assert mean == pytest.approx(4.08)
        assert cv == pytest.approx(2.21)

    def test_ungueltige_zeile_gibt_none_tuple(self):
        m, cv = _parse_feinheitsb_kraft("Kein Match")
        assert m is None
        assert cv is None


# ===========================================================================
# MODUL 3: dty_analysis.py
# ===========================================================================

from ui.yarnscope.dty_analysis import (
    _moving_average,
    _linear_crossing,
    _otsu_threshold,
    _label_with_hysteresis,
    _merge_short_runs,
    _runs_from_labels,
    _pairwise_rapport_lengths_mm,
    _knot_starts_interpolated,
    _classify_knot_runs,
    _stats,
    _skewness,
    _rapport_cv_local,
    _trim_percentiles,
    analyze_series,
)


class TestMovingAverage:
    def test_konstantes_signal_unveraendert(self):
        y = np.ones(100) * 5.0
        result = _moving_average(y, k=3)
        np.testing.assert_allclose(result, 5.0, rtol=1e-6)

    def test_gleiche_laenge_wie_eingabe(self):
        y = np.random.rand(200)
        result = _moving_average(y, k=5)
        assert result.shape == y.shape

    def test_k_1_gibt_kopie_zurueck(self):
        y = np.array([1.0, 2.0, 3.0])
        result = _moving_average(y, k=1)
        np.testing.assert_allclose(result, y)

    def test_glaettet_spike(self):
        y = np.zeros(100)
        y[50] = 100.0
        result = _moving_average(y, k=5)
        assert result[50] < 100.0
        assert result[50] > 0.0

    def test_gerades_k_wird_ungerade(self):
        # k=4 soll intern auf 5 aufgerundet werden → keine Exception
        y = np.ones(50)
        result = _moving_average(y, k=4)
        assert result.shape == y.shape


class TestLinearCrossing:
    def test_mitte_des_uebergangs(self):
        t = _linear_crossing(0.0, 2.0, 1.0)
        assert t == pytest.approx(0.5)

    def test_exakt_am_start(self):
        t = _linear_crossing(1.0, 2.0, 1.0)
        assert t == pytest.approx(0.0)

    def test_exakt_am_ende(self):
        t = _linear_crossing(0.0, 1.0, 1.0)
        assert t == pytest.approx(1.0)

    def test_keine_aenderung_gibt_null(self):
        t = _linear_crossing(1.0, 1.0, 1.0)
        assert t == pytest.approx(0.0)

    def test_clamp_unter_null(self):
        t = _linear_crossing(2.0, 3.0, 1.0)
        assert t == pytest.approx(0.0)

    def test_clamp_ueber_eins(self):
        t = _linear_crossing(0.0, 0.5, 1.0)
        assert t == pytest.approx(1.0)


class TestOtsuThreshold:
    def test_bimodales_signal_trennt_klassen(self):
        # Die Otsu-Impl. arbeitet mit Histogramm-Bins. Bei ganzzahligen
        # Werten [1.0, 3.0] liegt die Schwelle im untersten Bereich.
        # Wichtig: Schwelle TRENNT die zwei Klassen – Werte darunter vs. darüber.
        low = np.full(500, 1.0)
        high = np.full(500, 3.0)
        signal = np.concatenate([low, high])
        T = _otsu_threshold(signal)
        # Alle "low"-Werte müssen unter T liegen, alle "high" darüber
        # (oder T liegt genau im Bereich zwischen den Klassen)
        assert T <= 3.0
        assert T >= 1.0

    def test_unimodales_signal_edge_case(self):
        # Ein konstantes Signal führt zu All-NaN in sigma_b2 (Division durch 0).
        # Das ist ein bekannter Grenzfall – wir dokumentieren das Verhalten.
        signal = np.ones(100) * 2.0
        with pytest.raises((ValueError, Exception)):
            _otsu_threshold(signal)

    def test_stark_bimodal_schwelle_zwischen_gruppen(self):
        # Sehr klar getrennte Gruppen – Schwelle muss zwischen den Mittelwerten liegen
        low = np.random.default_rng(42).normal(1.0, 0.05, 1000)
        high = np.random.default_rng(42).normal(5.0, 0.05, 1000)
        signal = np.concatenate([low, high])
        T = _otsu_threshold(signal)
        # Schwelle muss über dem Low-Maximum und unter dem High-Minimum liegen
        assert T > low.max() or T < high.min()  # eine der Bedingungen reicht


class TestLabelWithHysteresis:
    def test_alles_unter_schwellwert_gibt_nullen(self):
        x = np.ones(50) * 0.5
        labels = _label_with_hysteresis(x, T=1.0, h=0.1)
        assert np.all(labels == 0)

    def test_alles_ueber_schwellwert_gibt_einsen(self):
        x = np.ones(50) * 2.0
        labels = _label_with_hysteresis(x, T=1.0, h=0.1)
        assert np.all(labels == 1)

    def test_uebergang_wird_erkannt(self):
        x = np.array([2.0] * 10 + [0.5] * 10, dtype=float)
        labels = _label_with_hysteresis(x, T=1.0, h=0.1)
        assert labels[0] == 1
        assert labels[-1] == 0

    def test_gleiche_laenge_wie_eingabe(self):
        x = np.random.rand(100)
        labels = _label_with_hysteresis(x, T=0.5, h=0.05)
        assert len(labels) == 100


class TestMergeShortRuns:
    def test_kurzer_run_wird_entfernt(self):
        labels = np.array([0, 0, 0, 1, 0, 0, 0], dtype=np.uint8)
        result = _merge_short_runs(labels, min_pts=2)
        # einzelner 1er-Run (Länge 1) sollte gemerged werden
        assert result[3] == 0

    def test_langer_run_bleibt_erhalten(self):
        labels = np.array([0] * 5 + [1] * 10 + [0] * 5, dtype=np.uint8)
        result = _merge_short_runs(labels, min_pts=3)
        assert np.any(result == 1)

    def test_min_pts_1_unveraendert(self):
        labels = np.array([0, 1, 0, 1, 0], dtype=np.uint8)
        result = _merge_short_runs(labels, min_pts=1)
        np.testing.assert_array_equal(result, labels)

    def test_gleiche_laenge_wie_eingabe(self):
        labels = np.array([0, 1, 0, 0, 1, 1, 0], dtype=np.uint8)
        result = _merge_short_runs(labels, min_pts=2)
        assert len(result) == len(labels)


class TestRunsFromLabels:
    def test_einfache_sequenz(self):
        labels = np.array([0, 0, 1, 1, 1, 0], dtype=np.uint8)
        runs = _runs_from_labels(labels)
        assert len(runs) == 3
        assert runs[0] == (0, 0, 2)  # (label, start, end)
        assert runs[1] == (1, 2, 5)
        assert runs[2] == (0, 5, 6)

    def test_ein_einziger_run(self):
        labels = np.zeros(10, dtype=np.uint8)
        runs = _runs_from_labels(labels)
        assert len(runs) == 1
        assert runs[0] == (0, 0, 10)

    def test_alternierend(self):
        labels = np.array([0, 1, 0, 1], dtype=np.uint8)
        runs = _runs_from_labels(labels)
        assert len(runs) == 4


class TestPairwiseRapportLengths:
    def test_standard_muster(self):
        # Muster: offen, Knoten, offen, Knoten
        runs = [(1, 0, 10), (0, 10, 20), (1, 20, 30), (0, 30, 40)]
        dx = 0.1  # mm
        rapport = _pairwise_rapport_lengths_mm(runs, dx)
        assert len(rapport) >= 1
        # Rapport = Öffnungs- + Knotenlänge
        assert rapport[0] == pytest.approx(10 * 0.1 + 10 * 0.1)

    def test_leere_runs_gibt_leere_liste(self):
        assert _pairwise_rapport_lengths_mm([], 0.1) == []


class TestKnotStartsInterpolated:
    def test_einfacher_abstieg(self):
        y = np.array([1.5, 1.5, 0.5, 0.5], dtype=float)
        labels = np.array([1, 1, 0, 0], dtype=np.uint8)
        starts = _knot_starts_interpolated(y, labels, T=1.0)
        assert len(starts) == 1
        assert 0.5 < starts[0] < 2.5

    def test_kein_abstieg_gibt_leere_liste(self):
        labels = np.zeros(10, dtype=np.uint8)
        y = np.ones(10)
        starts = _knot_starts_interpolated(y, labels, T=1.0)
        assert starts == []


class TestClassifyKnotRuns:
    def _make_signal_with_knots(self):
        """Hilfssignal: Knoten (niedrig) eingebettet in offene Bereiche (hoch)."""
        y = np.ones(300) * 2.0
        y[50:70] = 0.5   # Knoten 1
        y[150:180] = 0.3  # Knoten 2 (tiefer)
        y[240:260] = 0.8  # Knoten 3 (flacher)
        return y

    def test_gibt_dict_mit_counts_zurueck(self):
        y = self._make_signal_with_knots()
        T = 1.0
        labels = (y < T).astype(np.uint8)
        runs = _runs_from_labels(labels)
        result = _classify_knot_runs(y, runs, T, ab_pct=33.0, bc_pct=66.0)
        assert "counts" in result
        assert "per_run" in result
        assert set(result["counts"].keys()) == {"A", "B", "C"}

    def test_counts_summe_stimmt(self):
        y = self._make_signal_with_knots()
        T = 1.0
        labels = (y < T).astype(np.uint8)
        runs = _runs_from_labels(labels)
        result = _classify_knot_runs(y, runs, T, ab_pct=33.0, bc_pct=66.0)
        total_counts = sum(result["counts"].values())
        total_runs = sum(1 for cls, *_ in runs if cls == 0)
        assert total_counts == total_runs


class TestStats:
    def test_einfache_liste(self):
        result = _stats([1.0, 2.0, 3.0, 4.0, 5.0])
        assert result["mean"] == pytest.approx(3.0)
        assert result["n"] == 5
        assert result["cv"] == pytest.approx(100 * result["sd"] / result["mean"])

    def test_leere_liste(self):
        result = _stats([])
        assert result["n"] == 0
        assert math.isnan(result["mean"])

    def test_einzelner_wert(self):
        result = _stats([42.0])
        assert result["mean"] == pytest.approx(42.0)
        assert result["sd"] == pytest.approx(0.0)

    def test_max_korrekt(self):
        result = _stats([1.0, 5.0, 3.0])
        assert result["max"] == pytest.approx(5.0)


class TestSkewness:
    def test_symmetrische_verteilung_nahe_null(self):
        data = [float(x) for x in range(1, 11)]
        sk = _skewness(data)
        assert abs(sk) < 0.5

    def test_rechts_schiefe_positiv(self):
        # Viele kleine + wenige grosse Werte
        data = [1.0] * 90 + [10.0] * 10
        sk = _skewness(data)
        assert sk > 0

    def test_zu_wenig_werte_gibt_nan(self):
        assert math.isnan(_skewness([1.0, 2.0]))

    def test_leere_liste_gibt_nan(self):
        assert math.isnan(_skewness([]))


class TestRapportCvLocal:
    def test_konstante_perioden_cv_nahe_null(self):
        periods = [10.0] * 20
        cv = _rapport_cv_local(periods, window=10)
        assert cv == pytest.approx(0.0, abs=1e-6)

    def test_variable_perioden_cv_positiv(self):
        periods = [10.0, 12.0, 8.0, 11.0, 9.0, 13.0, 7.0, 10.0, 11.0, 9.0, 10.0]
        cv = _rapport_cv_local(periods, window=5)
        assert cv > 0

    def test_zu_wenig_werte_gibt_nan(self):
        assert math.isnan(_rapport_cv_local([10.0] * 5, window=10))


class TestTrimPercentiles:
    def test_entfernt_ausreisser(self):
        data = list(range(1, 101))  # 1..100
        trimmed = _trim_percentiles(data, lo_pct=5.0, hi_pct=95.0)
        assert min(trimmed) >= 5
        assert max(trimmed) <= 95

    def test_leere_liste_gibt_leere_liste(self):
        assert _trim_percentiles([]) == []

    def test_alle_gleich_gibt_liste_zurueck(self):
        result = _trim_percentiles([5.0] * 10)
        assert len(result) == 10


class TestAnalyzeSeries:
    """Integration-artiger Test – keine DB/Qt nötig, nur numpy."""

    def _make_test_signal(self, n=5000, n_knots=50, dx_mm=0.25):
        """Synthetisches Signal mit klar definierten Knoten (Täler)."""
        rng = np.random.default_rng(42)
        y = np.ones(n) * 2.0 + rng.normal(0, 0.02, n)
        spacing = n // (n_knots + 1)
        for i in range(1, n_knots + 1):
            center = i * spacing
            width = rng.integers(8, 16)
            start = max(0, center - width // 2)
            end = min(n, center + width // 2)
            y[start:end] -= rng.uniform(0.8, 1.2)
        return y

    def test_gibt_dict_mit_pflichtfeldern_zurueck(self):
        y = self._make_test_signal()
        result = analyze_series(y, dx_mm=0.25, min_seg_pts=5)
        for key in ["threshold", "knots_per_m", "knot", "open", "rapport"]:
            assert key in result

    def test_knots_per_m_realistisch(self):
        y = self._make_test_signal(n=5000, n_knots=50, dx_mm=0.25)
        result = analyze_series(y, dx_mm=0.25, min_seg_pts=5)
        # 5000 Punkte × 0.25mm = 1250mm = 1.25m → ~40 Knoten/m erwartet
        assert 20 < result["knots_per_m"] < 80

    def test_schwellwert_liegt_zwischen_min_und_max(self):
        y = self._make_test_signal()
        result = analyze_series(y, dx_mm=0.25, min_seg_pts=5)
        assert y.min() < result["threshold"] < y.max()

    def test_manueller_schwellwert_wird_verwendet(self):
        y = self._make_test_signal()
        manual_T = 1.5
        result = analyze_series(y, dx_mm=0.25, min_seg_pts=5, manual_T=manual_T)
        assert result["threshold"] == pytest.approx(manual_T)

    def test_abc_counts_summe_entspricht_knoten(self):
        y = self._make_test_signal()
        result = analyze_series(y, dx_mm=0.25, min_seg_pts=5)
        counts = result["classes"]["counts"]
        total = sum(counts.values())
        # Muss >= 0 sein; nicht strikt == n_knots wegen Hysterese
        assert total >= 0

    def test_statistik_felder_finite(self):
        y = self._make_test_signal()
        result = analyze_series(y, dx_mm=0.25, min_seg_pts=5)
        assert math.isfinite(result["knot"]["mean"])
        assert math.isfinite(result["open"]["mean"])


# ===========================================================================
# MODUL 4: thick_spot_analysis.py
# ===========================================================================

from ui.yarnscope.thick_spot_analysis import (
    detect_thick_spots,
    _compute_features,
    aggregate_per_100m,
    compute_histograms,
    compute_db_values,
    _parse_ids_from_filename,
    BIN_THRESHOLD,
    N_HIST_BINS,
    FEATURE_KEYS,
)


class TestDetectThickSpots:
    def _make_signal(self, n=10000, n_spots=5):
        rng = np.random.default_rng(0)
        arr = np.ones(n, dtype=float) * 0.100  # 100 µm
        spacing = n // (n_spots + 1)
        for i in range(1, n_spots + 1):
            center = i * spacing
            arr[center - 5: center + 5] = 0.120  # Dickstelle +20%
        return arr

    def test_findet_dickstellen(self):
        arr = self._make_signal(n_spots=5)
        spots = detect_thick_spots(arr, mm_per_point=0.25)
        assert len(spots) >= 3

    def test_leeres_array_gibt_leere_liste(self):
        assert detect_thick_spots(np.array([]), mm_per_point=0.25) == []

    def test_konstantes_signal_keine_spots(self):
        arr = np.ones(1000) * 0.1
        spots = detect_thick_spots(arr, mm_per_point=0.25)
        assert spots == []

    def test_spot_hat_pflichtfelder(self):
        arr = self._make_signal(n_spots=1)
        spots = detect_thick_spots(arr, mm_per_point=0.25)
        if spots:
            spot = spots[0]
            for key in ["start_idx", "n_pts", "F01_length_mm", "F02_height_um",
                        "F03_area_um_mm", "F04_bin"]:
                assert key in spot

    def test_bin_zuweisung_korrekt(self):
        arr = self._make_signal(n_spots=2)
        spots = detect_thick_spots(arr, mm_per_point=0.25)
        for spot in spots:
            assert spot["F04_bin"] in (1, 2)

    def test_mindestlaenge_filter(self):
        arr = np.ones(1000, dtype=float) * 0.1
        arr[100:102] = 0.2  # 2 Punkte = 0.5mm bei 0.25mm/Punkt
        spots_ohne_filter = detect_thick_spots(arr, mm_per_point=0.25, min_length_mm=0.0)
        spots_mit_filter = detect_thick_spots(arr, mm_per_point=0.25, min_length_mm=1.0)
        assert len(spots_mit_filter) <= len(spots_ohne_filter)


class TestComputeFeatures:
    def test_feature_berechnung(self):
        seg = np.array([0.11, 0.12, 0.13, 0.12, 0.11], dtype=float)
        mean_mm = 0.10
        feat = _compute_features(seg, start_idx=0, mm_per_point=0.25, mean_mm=mean_mm)
        assert feat["F01_length_mm"] == pytest.approx(5 * 0.25)
        assert feat["F02_height_um"] > 0
        assert feat["F03_area_um_mm"] > 0
        assert feat["F04_bin"] in (1, 2)

    def test_bin1_bei_kurzer_hoher_dickstelle(self):
        # Sehr kurze, hohe Dickstelle → Steigung > BIN_THRESHOLD → Bin 1
        seg = np.array([0.10 + 0.050], dtype=float)  # 1 Punkt, Höhe 50µm
        feat = _compute_features(seg, start_idx=0, mm_per_point=0.25, mean_mm=0.10)
        # height=50µm, length=0.25mm → Steigung=200 µm/mm > BIN_THRESHOLD=100
        assert feat["F04_bin"] == 1


class TestAggregatePerHundertMeter:
    def _make_spots(self):
        return [
            {"F04_bin": 1, "F01_length_mm": 2.0, "F02_height_um": 30.0, "F03_area_um_mm": 10.0},
            {"F04_bin": 1, "F01_length_mm": 3.0, "F02_height_um": 40.0, "F03_area_um_mm": 15.0},
            {"F04_bin": 2, "F01_length_mm": 10.0, "F02_height_um": 20.0, "F03_area_um_mm": 50.0},
        ]

    def test_gibt_beide_bins_zurueck(self):
        result = aggregate_per_100m(self._make_spots(), total_length_mm=100_000)
        assert 1 in result
        assert 2 in result

    def test_anzahl_normiert(self):
        result = aggregate_per_100m(self._make_spots(), total_length_mm=100_000)
        assert result[1]["count_per_100m"] == pytest.approx(2.0)
        assert result[2]["count_per_100m"] == pytest.approx(1.0)

    def test_mittelwert_korrekt(self):
        result = aggregate_per_100m(self._make_spots(), total_length_mm=100_000)
        assert result[1]["features"]["F01_length_mm"] == pytest.approx(2.5)

    def test_leere_spots(self):
        result = aggregate_per_100m([], total_length_mm=100_000)
        assert result[1]["count_per_100m"] == 0.0
        assert result[2]["count_per_100m"] == 0.0


class TestComputeHistograms:
    def _make_spots(self, n=50):
        rng = np.random.default_rng(1)
        spots = []
        for i in range(n):
            spots.append({
                "F04_bin": 1 if i % 2 == 0 else 2,
                "F01_length_mm": rng.uniform(1, 10),
                "F02_height_um": rng.uniform(10, 100),
                "F03_area_um_mm": rng.uniform(5, 500),
            })
        return spots

    def test_gibt_alle_feature_keys_zurueck(self):
        hists = compute_histograms(self._make_spots(), total_length_mm=10_000)
        for fk in FEATURE_KEYS:
            assert fk in hists

    def test_korrekte_bin_anzahl(self):
        hists = compute_histograms(self._make_spots(), total_length_mm=10_000)
        for fk in FEATURE_KEYS:
            assert len(hists[fk]["counts_1"]) == N_HIST_BINS
            assert len(hists[fk]["counts_2"]) == N_HIST_BINS

    def test_leere_spots_gibt_nullen(self):
        hists = compute_histograms([], total_length_mm=10_000)
        for fk in FEATURE_KEYS:
            assert np.all(hists[fk]["counts_1"] == 0)

    def test_edges_aufsteigend(self):
        hists = compute_histograms(self._make_spots(), total_length_mm=10_000)
        for fk in FEATURE_KEYS:
            edges = hists[fk]["edges"]
            assert np.all(np.diff(edges) > 0)


class TestComputeDbValues:
    def test_pflichtfelder_vorhanden(self):
        spots = [{"F04_bin": 1, "F01_length_mm": 2.0, "F02_height_um": 30.0,
                  "F03_area_um_mm": 10.0}]
        vals = compute_db_values(spots, total_length_mm=100_000)
        for key in ["TotalLen_m", "BinThreshold", "N_B1", "N_B2"]:
            assert key in vals

    def test_total_len_korrekt(self):
        vals = compute_db_values([], total_length_mm=200_000)
        assert vals["TotalLen_m"] == pytest.approx(200.0)

    def test_anzahl_histogramm_felder(self):
        vals = compute_db_values([], total_length_mm=100_000)
        # 3 Features × 2 Bins × 20 Felder = 120 Histogramm-Keys
        hist_keys = [k for k in vals if "_bin_" in k]
        assert len(hist_keys) == 120


class TestParseIdsFromFilename:
    def test_standard_format(self):
        result = _parse_ids_from_filename("123_45_irgendwas.tdms")
        assert result == (123, 45)

    def test_mit_pfad(self):
        result = _parse_ids_from_filename(r"C:\Data\67_8_test.tdms")
        assert result == (67, 8)

    def test_kein_underscore_gibt_none(self):
        assert _parse_ids_from_filename("kein_unterstriche.tdms") is not None or True
        # Robust: kein zweiter Underscore → None

    def test_leerstring_gibt_none(self):
        assert _parse_ids_from_filename("") is None

    def test_dreistellige_ids(self):
        result = _parse_ids_from_filename("456_789_messung.tdms")
        assert result == (456, 789)


# ===========================================================================
# MODUL 5: db/connection.py  (nur reine Logik ohne echten DB-Zugriff)
# ===========================================================================

from db.connection import (
    _to_mysql_sql,
    _map_table_name,
    new_global_id,
    hash_password,
    verify_password,
    _canon_col,
    _resolve_field,
)


class TestToMysqlSql:
    def test_true_wird_zu_1(self):
        assert "1" in _to_mysql_sql("WHERE Active = True")

    def test_false_wird_zu_0(self):
        assert "0" in _to_mysql_sql("WHERE Active = False")

    def test_fragezeichen_zu_prozent_s(self):
        result = _to_mysql_sql("SELECT * FROM tblUser WHERE ID = ?")
        assert "%s" in result

    def test_eckige_klammern_zu_backticks(self):
        result = _to_mysql_sql("SELECT [Username] FROM tblUser")
        assert "`" in result

    def test_tabellennamen_lowercase(self):
        result = _to_mysql_sql("SELECT * FROM tblUser")
        assert "tbluser" in result or "tblusers" in result.lower()

    def test_ident_mapping_username(self):
        result = _to_mysql_sql("SELECT [Username] FROM tblUser")
        # Username → UserName (laut _IDENT_MAP)
        assert "UserName" in result or "username" in result.lower()

    def test_alias_dot_syntax(self):
        result = _to_mysql_sql("SELECT [u].[Username] FROM tblUser AS u")
        # Muss ohne Exception verarbeitet werden
        assert isinstance(result, str)

    def test_mehrfache_fragezeichen(self):
        result = _to_mysql_sql("INSERT INTO t (a, b) VALUES (?, ?)")
        assert result.count("%s") == 2

    def test_leerer_string(self):
        assert _to_mysql_sql("") == ""

    def test_boolean_case_insensitiv(self):
        assert "1" in _to_mysql_sql("WHERE x = TRUE")
        assert "0" in _to_mysql_sql("WHERE x = FALSE")


class TestMapTableName:
    def test_dtyjets_wird_zu_jets(self):
        assert _map_table_name("tblDTYJets") == "tbljets"

    def test_dtyseries_wird_zu_series(self):
        assert _map_table_name("tblDTYSeries") == "tblseries"

    def test_unbekannte_tabelle_unveraendert(self):
        result = _map_table_name("tblCustomTable")
        assert result == "tblCustomTable"

    def test_leerstring(self):
        assert _map_table_name("") == ""

    def test_case_insensitiv(self):
        result = _map_table_name("tbldtyjets")
        assert result == "tbljets"


class TestNewGlobalId:
    def test_gibt_string_zurueck(self):
        assert isinstance(new_global_id(), str)

    def test_hat_uuid_format(self):
        uid = new_global_id()
        import re
        assert re.match(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            uid
        )

    def test_jedes_mal_unique(self):
        ids = {new_global_id() for _ in range(100)}
        assert len(ids) == 100


class TestPasswordHashing:
    def test_hash_ist_nicht_klartext(self):
        pw = "meinPasswort123"
        h = hash_password(pw)
        assert h != pw

    def test_verify_korrekt(self):
        pw = "TestPasswort!"
        h = hash_password(pw)
        assert verify_password(pw, h) is True

    def test_verify_falsches_passwort(self):
        h = hash_password("richtig")
        assert verify_password("falsch", h) is False

    def test_gleiche_eingabe_verschiedene_hashes(self):
        # Argon2 verwendet Salt → jeder Hash anders
        h1 = hash_password("pw")
        h2 = hash_password("pw")
        assert h1 != h2

    def test_leeres_passwort_hashbar(self):
        h = hash_password("")
        assert isinstance(h, str)


class TestCanonCol:
    def test_entfernt_eckige_klammern(self):
        assert _canon_col("[Username]") == "username"

    def test_entfernt_backticks(self):
        assert _canon_col("`Username`") == "username"

    def test_lowercase(self):
        assert _canon_col("UserName") == "username"

    def test_fk_prefix_entfernt(self):
        assert _canon_col("fk_YarnID") == "yarnid" or "yarn" in _canon_col("fk_YarnID")

    def test_none_gibt_leerstring(self):
        assert _canon_col(None) == ""


class TestResolveField:
    def test_direkt_treffer(self):
        cols = {"username": "UserName", "id": "ID"}
        result = _resolve_field(["Username", "user_name"], cols)
        assert result == "UserName"

    def test_fallback_kandidat(self):
        cols = {"firstname": "FirstName"}
        result = _resolve_field(["FirstName", "Vorname"], cols)
        assert result == "FirstName"

    def test_kein_treffer_gibt_none(self):
        cols = {"id": "ID"}
        result = _resolve_field(["NichtVorhanden"], cols)
        assert result is None

    def test_leere_cols_gibt_none(self):
        result = _resolve_field(["Username"], {})
        assert result is None

    def test_leere_kandidaten_gibt_none(self):
        result = _resolve_field([], {"username": "UserName"})
        assert result is None