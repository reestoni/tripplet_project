"""
TrippleT – Stufe 4 UI-Tests (pytest-qt)
=========================================
Abdeckung:
  - LoginScreen              Widget-Zustand, Button-Logik, Passwort-Sicherheitsprüfung
  - ManageJetsScreen         Widgets vorhanden, Suche/Filter, JetsTableModel, _to_bool/_to_int_like
  - ManageYarnScreen         Widgets vorhanden, YarnTableModel, DPF-Berechnung
  - NewJetScreen             Formular-Aufbau, Editor-Typen, Pflichtfeld-Validierung

Keine echte DB nötig – alle DB-Aufrufe werden mit unittest.mock.patch gemockt.

Setup: pytest muss aus dem TrippleT/-Projektordner ausgeführt werden:
    cd TrippleT
    pytest tests/test_ttt_ui.py -v
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock


def _find_ttt_root():
    """Findet das ttt/-Verzeichnis (enthält ui/ und db/)."""
    candidates = [
        # Standard: Tests liegen in TrippleT/tests/, Code in TrippleT/ttt/
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ttt"),
        # Fallback: pytest wird direkt aus ttt/ gestartet
        os.getcwd(),
        # CI / bekannte Pfade
        "/home/claude/ttt/ttt",
    ]
    for c in candidates:
        c = os.path.abspath(c)
        if os.path.isdir(os.path.join(c, "ui")):
            return c
    raise RuntimeError("ttt/-Verzeichnis nicht gefunden – pytest aus TrippleT/ starten.")


_TTT_ROOT = _find_ttt_root()
if _TTT_ROOT not in sys.path:
    sys.path.insert(0, _TTT_ROOT)


# ===========================================================================
# SCREEN 1: LoginScreen
# ===========================================================================

class TestLoginScreenWidgets:
    """Widget-Zustand ohne jede DB-Interaktion."""

    @pytest.fixture
    def login(self, qtbot):
        from ui.screen_login import LoginScreen
        w = LoginScreen(on_success=lambda info: None, on_change_pw=lambda u: None)
        qtbot.addWidget(w)
        w.show()
        return w

    def test_login_button_initial_disabled(self, login):
        assert not login.btn_login.isEnabled()

    def test_login_button_enabled_wenn_beide_felder_gefuellt(self, qtbot, login):
        login.txt_user.setText("jens")
        login.txt_pw.setText("geheim")
        assert login.btn_login.isEnabled()

    def test_login_button_disabled_wenn_nur_user(self, login):
        login.txt_user.setText("jens")
        assert not login.btn_login.isEnabled()

    def test_login_button_disabled_wenn_nur_passwort(self, login):
        login.txt_pw.setText("geheim")
        assert not login.btn_login.isEnabled()

    def test_login_button_disabled_nach_leeren(self, login):
        login.txt_user.setText("jens")
        login.txt_pw.setText("geheim")
        assert login.btn_login.isEnabled()
        login.txt_user.clear()
        assert not login.btn_login.isEnabled()

    def test_login_button_disabled_bei_nur_leerzeichen(self, login):
        login.txt_user.setText("   ")
        login.txt_pw.setText("geheim")
        assert not login.btn_login.isEnabled()

    def test_passwort_feld_ist_verdeckt(self, login):
        from PySide6.QtWidgets import QLineEdit
        assert login.txt_pw.echoMode() == QLineEdit.Password

    def test_change_password_button_vorhanden(self, login):
        assert login.btn_change is not None
        assert login.btn_change.isVisible()

    def test_username_placeholder_vorhanden(self, login):
        assert login.txt_user.placeholderText() != ""

    def test_passwort_placeholder_vorhanden(self, login):
        assert login.txt_pw.placeholderText() != ""


class TestLoginScreenSicherheit:
    """Sicherheitslogik: Passwort == Benutzername blockiert, DB-Fehler behandelt."""

    @pytest.fixture
    def login(self, qtbot):
        from ui.screen_login import LoginScreen
        self.change_pw_calls = []
        w = LoginScreen(
            on_success=lambda info: None,
            on_change_pw=lambda u: self.change_pw_calls.append(u),
        )
        qtbot.addWidget(w)
        w.show()
        return w

    def test_passwort_gleich_username_oeffnet_change_pw(self, login):
        login.txt_user.setText("jens")
        login.txt_pw.setText("jens")
        with patch("ui.screen_login.QMessageBox") as mock_mb:
            mock_mb.return_value = MagicMock()
            mock_mb.return_value.exec.return_value = None
            login._attempt_login()
        assert "jens" in self.change_pw_calls

    def test_passwort_gleich_username_case_insensitiv(self, login):
        login.txt_user.setText("Jens")
        login.txt_pw.setText("jens")
        with patch("ui.screen_login.QMessageBox") as mock_mb:
            mock_mb.return_value = MagicMock()
            mock_mb.return_value.exec.return_value = None
            login._attempt_login()
        assert len(self.change_pw_calls) == 1

    def test_db_fehler_zeigt_fehlermeldung(self, login):
        login.txt_user.setText("jens")
        login.txt_pw.setText("anderes_pw")
        with patch("ui.screen_login.check_credentials", side_effect=Exception("DB offline")):
            with patch("ui.screen_login.show_error") as mock_err:  # friendly error box (2026-10-16)
                login._attempt_login()
                mock_err.assert_called_once()
                assert "could not connect" in mock_err.call_args[0][2]

    def test_erfolgreicher_login_ruft_callback(self, qtbot):
        from ui.screen_login import LoginScreen
        success_data = []
        w = LoginScreen(
            on_success=lambda info: success_data.append(info),
            on_change_pw=lambda u: None,
        )
        qtbot.addWidget(w)
        w.txt_user.setText("jens")
        w.txt_pw.setText("richtig")
        with patch("ui.screen_login.check_credentials", return_value=True), \
             patch("ui.screen_login.get_user_access_level", return_value=2), \
             patch("ui.screen_login.get_user_access_right", return_value="User"), \
             patch("ui.screen_login.get_user_admin_box", return_value=False), \
             patch("ui.screen_login.get_user_first_last_name", return_value=("Jens", "S")), \
             patch("ui.screen_login.get_user_accent_colour", return_value=None), \
             patch("ui.screen_login.cleanup_draft_experiment_requests", return_value={}), \
             patch("ui.screen_login.get_user_id", return_value=42):
            w._attempt_login()
        assert len(success_data) == 1
        assert success_data[0]["username"] == "jens"
        assert success_data[0]["access_level"] == 2

    def test_falsches_passwort_ruft_keinen_success_callback(self, qtbot):
        from ui.screen_login import LoginScreen
        success_data = []
        w = LoginScreen(
            on_success=lambda info: success_data.append(info),
            on_change_pw=lambda u: None,
        )
        qtbot.addWidget(w)
        w.txt_user.setText("jens")
        w.txt_pw.setText("falsch")
        with patch("ui.screen_login.check_credentials", return_value=False), \
             patch("ui.screen_login.is_user_active", return_value=True), \
             patch("ui.screen_login.QMessageBox") as mock_mb:
            mock_mb.warning = MagicMock()
            w._attempt_login()
        assert len(success_data) == 0


# ===========================================================================
# SCREEN 2: ManageJetsScreen – Widgets + Hilfsfunktionen
# ===========================================================================

class TestJetsScreenWidgets:
    """Grundlegende Widget-Präsenz."""

    @pytest.fixture
    def screen(self, qtbot):
        from ui.screen_manage_jets import ManageJetsScreen
        with patch.object(ManageJetsScreen, "reload_data", return_value=None):
            w = ManageJetsScreen(on_back_home=lambda: None)
            qtbot.addWidget(w)
            w.show()
        return w

    def test_search_edit_vorhanden(self, screen):
        assert screen.search_edit is not None
        assert screen.search_edit.isVisible()

    def test_btn_new_vorhanden(self, screen):
        assert screen.btn_new is not None

    def test_btn_save_vorhanden(self, screen):
        assert screen.btn_save is not None

    def test_btn_delete_vorhanden(self, screen):
        assert screen.btn_delete is not None

    def test_btn_copy_vorhanden(self, screen):
        assert screen.btn_copy is not None

    def test_btn_reload_vorhanden(self, screen):
        assert screen.btn_reload is not None

    def test_table_vorhanden(self, screen):
        assert screen.table is not None


class TestJetsTableModel:
    """JetsTableModel ohne echten Screen – reines Modell-Testing."""

    @pytest.fixture
    def model(self):
        from ui.screen_manage_jets import JetsTableModel
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        rows = [
            {"ID": 1, "Jet": "J-100", "StandardJet": True,  "AirPressure": 4.5},
            {"ID": 2, "Jet": "J-200", "StandardJet": False, "AirPressure": 5.0},
            {"ID": 3, "Jet": "J-300", "StandardJet": True,  "AirPressure": 3.5},
        ]
        headers = ["ID", "Jet", "StandardJet", "AirPressure"]
        return JetsTableModel(rows=rows, headers=headers, id_column="ID")

    def test_row_count(self, model):
        assert model.rowCount() == 3

    def test_column_count(self, model):
        assert model.columnCount() == 4

    def test_header_data(self, model):
        from PySide6.QtCore import Qt
        assert model.headerData(1, Qt.Horizontal) == "Jet"
        assert model.headerData(0, Qt.Horizontal) == "ID"

    def test_data_display_role(self, model):
        from PySide6.QtCore import Qt
        assert model.data(model.index(0, 1), Qt.DisplayRole) == "J-100"
        assert model.data(model.index(1, 1), Qt.DisplayRole) == "J-200"

    def test_setdata_markiert_dirty(self, model):
        from PySide6.QtCore import Qt
        model.setData(model.index(0, 1), "J-100-NEU", Qt.EditRole)
        assert len(model.dirty_rows()) == 1

    def test_dirty_rows_leer_initial(self, model):
        assert model.dirty_rows() == []

    def test_clear_dirty(self, model):
        from PySide6.QtCore import Qt
        model.setData(model.index(0, 1), "Neu", Qt.EditRole)
        assert len(model.dirty_rows()) == 1
        model.clear_dirty()
        assert model.dirty_rows() == []

    def test_mehrere_dirty_rows(self, model):
        from PySide6.QtCore import Qt
        model.setData(model.index(0, 1), "A", Qt.EditRole)
        model.setData(model.index(2, 1), "B", Qt.EditRole)
        assert len(model.dirty_rows()) == 2

    def test_headers_property(self, model):
        assert "Jet" in model.headers()
        assert "ID" in model.headers()

    def test_invalid_index_gibt_none(self, model):
        from PySide6.QtCore import Qt, QModelIndex
        assert model.data(QModelIndex(), Qt.DisplayRole) is None


class TestJetsHelperFunctions:
    """_to_bool und _to_int_like – keine QApplication nötig."""

    def test_to_bool_true_werte(self):
        from ui.screen_manage_jets import _to_bool
        for v in [True, 1, -1, "true", "yes", "y", "1", "True", "YES", "T"]:
            assert _to_bool(v) is True, f"Erwartet True für {v!r}"

    def test_to_bool_false_werte(self):
        from ui.screen_manage_jets import _to_bool
        for v in [False, 0, None, "false", "no", "0", "", "False", "NO"]:
            assert _to_bool(v) is False, f"Erwartet False für {v!r}"

    def test_to_bool_decimal_true(self):
        from ui.screen_manage_jets import _to_bool
        from decimal import Decimal
        assert _to_bool(Decimal("1")) is True
        assert _to_bool(Decimal("5")) is True

    def test_to_bool_decimal_false(self):
        from ui.screen_manage_jets import _to_bool
        from decimal import Decimal
        assert _to_bool(Decimal("0")) is False

    def test_to_int_like_int(self):
        from ui.screen_manage_jets import _to_int_like
        assert _to_int_like(42) == 42
        assert _to_int_like(0) == 0

    def test_to_int_like_float_ganzzahlig(self):
        from ui.screen_manage_jets import _to_int_like
        assert _to_int_like(5.0) == 5
        assert _to_int_like(100.0) == 100

    def test_to_int_like_float_nicht_ganzzahlig_gibt_none(self):
        from ui.screen_manage_jets import _to_int_like
        assert _to_int_like(5.7) is None
        assert _to_int_like(3.14) is None

    def test_to_int_like_string(self):
        from ui.screen_manage_jets import _to_int_like
        assert _to_int_like("12") == 12

    def test_to_int_like_string_mit_punkt_null(self):
        from ui.screen_manage_jets import _to_int_like
        assert _to_int_like("7.0") == 7

    def test_to_int_like_decimal(self):
        from ui.screen_manage_jets import _to_int_like
        from decimal import Decimal
        assert _to_int_like(Decimal("9")) == 9

    def test_to_int_like_ungueltig_gibt_none(self):
        from ui.screen_manage_jets import _to_int_like
        assert _to_int_like("abc") is None

    def test_to_int_like_none_gibt_none(self):
        from ui.screen_manage_jets import _to_int_like
        assert _to_int_like(None) is None


class TestJetsSearch:
    """Suchfeld filtert Proxy-Model korrekt."""

    @pytest.fixture
    def screen_mit_daten(self, qtbot):
        from ui.screen_manage_jets import ManageJetsScreen, JetsTableModel, MultiColumnFilterProxy
        from PySide6.QtCore import Qt

        rows = [
            {"ID": 1, "Jet": "Standard-100", "AirPressure": 4.0},
            {"ID": 2, "Jet": "Premium-200",  "AirPressure": 5.0},
            {"ID": 3, "Jet": "Standard-300", "AirPressure": 3.0},
        ]
        headers = ["ID", "Jet", "AirPressure"]

        with patch.object(ManageJetsScreen, "reload_data", return_value=None):
            w = ManageJetsScreen(on_back_home=lambda: None)
            qtbot.addWidget(w)

        # Muss MultiColumnFilterProxy sein (nicht der generische QSortFilterProxyModel):
        # _on_search_changed() ruft proxy.set_column_filter(...) auf, und
        # _configure_filter_column() ermittelt self._jet_filter_col aus den Headers –
        # ohne beides bleibt die Suche wirkungslos (Proxy zeigt immer alle Zeilen).
        w.model = JetsTableModel(rows=rows, headers=headers, id_column="ID")
        w.proxy = MultiColumnFilterProxy(w)
        w.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        w.proxy.setSourceModel(w.model)
        w._configure_filter_column()
        w.table.setModel(w.proxy)
        return w

    def test_leere_suche_zeigt_alle(self, screen_mit_daten):
        screen_mit_daten._on_search_changed("")
        assert screen_mit_daten.proxy.rowCount() == 3

    def test_suche_filtert_auf_einen_treffer(self, screen_mit_daten):
        screen_mit_daten._on_search_changed("Premium")
        assert screen_mit_daten.proxy.rowCount() == 1

    def test_suche_filtert_auf_mehrere_treffer(self, screen_mit_daten):
        screen_mit_daten._on_search_changed("Standard")
        assert screen_mit_daten.proxy.rowCount() == 2

    def test_suche_case_insensitiv(self, screen_mit_daten):
        screen_mit_daten._on_search_changed("standard")
        assert screen_mit_daten.proxy.rowCount() == 2

    def test_suche_ohne_treffer(self, screen_mit_daten):
        screen_mit_daten._on_search_changed("XYZ_NICHT_VORHANDEN")
        assert screen_mit_daten.proxy.rowCount() == 0

    def test_suche_zuruecksetzen(self, screen_mit_daten):
        screen_mit_daten._on_search_changed("Premium")
        assert screen_mit_daten.proxy.rowCount() == 1
        screen_mit_daten._on_search_changed("")
        assert screen_mit_daten.proxy.rowCount() == 3


# ===========================================================================
# SCREEN 3: ManageYarnScreen – DPF-Berechnung + Modell
# ===========================================================================

class TestYarnTableModelDpf:
    """YarnTableModel._compute_dpf und Flags – kein Qt-Screen nötig."""

    @pytest.fixture
    def model(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        with patch("ui.screen_manage_yarn.fetch_all", return_value=[]), \
             patch("ui.screen_manage_yarn.get_columns_map", return_value={}):
            from ui.screen_manage_yarn import YarnTableModel

        rows = [
            {"ID": 1, "GarnName": "PA6.6", "EndTiterDtex": 78.0,  "NumberOfFilaments": 24, "DPFdtex": None},
            {"ID": 2, "GarnName": "PET",   "EndTiterDtex": None,   "NumberOfFilaments": 36, "DPFdtex": None},
            {"ID": 3, "GarnName": "PA6",   "EndTiterDtex": 100.0,  "NumberOfFilaments": 0,  "DPFdtex": None},
        ]
        headers = ["ID", "GarnName", "EndTiterDtex", "NumberOfFilaments", "DPFdtex"]
        return YarnTableModel(rows=rows, headers=headers, id_column="ID")

    def test_dpf_berechnung_korrekt(self, model):
        result = model._compute_dpf(0)
        assert abs(result - 78.0 / 24) < 0.001

    def test_dpf_bei_fehlendem_endtiter_gibt_none(self, model):
        assert model._compute_dpf(1) is None

    def test_dpf_bei_null_filamenten_gibt_none(self, model):
        assert model._compute_dpf(2) is None

    def test_dpf_erkennt_spalten_korrekt(self, model):
        assert model._dpf_col == "DPFdtex"
        assert model._endtiter_col == "EndTiterDtex"
        assert model._filaments_col == "NumberOfFilaments"

    def test_row_count(self, model):
        assert model.rowCount() == 3

    def test_column_count(self, model):
        assert model.columnCount() == 5

    def test_header_data(self, model):
        from PySide6.QtCore import Qt
        assert model.headerData(1, Qt.Horizontal) == "GarnName"
        assert model.headerData(4, Qt.Horizontal) == "DPFdtex"

    def test_dpf_spalte_ist_read_only(self, model):
        from PySide6.QtCore import Qt
        flags = model.flags(model.index(0, 4))  # DPFdtex
        assert not bool(flags & Qt.ItemIsEditable)

    def test_garnname_spalte_ist_editierbar(self, model):
        from PySide6.QtCore import Qt
        flags = model.flags(model.index(0, 1))  # GarnName
        assert bool(flags & Qt.ItemIsEditable)

    def test_dirty_tracking_nach_setdata(self, model):
        from PySide6.QtCore import Qt
        model.setData(model.index(0, 1), "PA6.6-NEU", Qt.EditRole)
        assert len(model.dirty_rows()) == 1

    def test_dpf_spalte_setdata_abgelehnt(self, model):
        from PySide6.QtCore import Qt
        original_val = model._rows[0].get("DPFdtex")
        result = model.setData(model.index(0, 4), 99.9, Qt.EditRole)
        assert result is False or model._rows[0].get("DPFdtex") == original_val


class TestManageYarnScreenWidgets:
    """Grundlegende Widget-Präsenz im ManageYarnScreen."""

    @pytest.fixture
    def screen(self, qtbot):
        from ui.screen_manage_yarn import ManageYarnScreen
        with patch("ui.screen_manage_yarn.fetch_all", return_value=[]), \
             patch("ui.screen_manage_yarn.get_columns_map", return_value={}):
            w = ManageYarnScreen(on_back_home=lambda: None)
            qtbot.addWidget(w)
            w.show()
        return w

    def test_btn_new_vorhanden(self, screen):
        assert screen.btn_new is not None

    def test_btn_save_vorhanden(self, screen):
        assert screen.btn_save is not None

    def test_btn_delete_vorhanden(self, screen):
        assert screen.btn_delete is not None

    def test_btn_reload_vorhanden(self, screen):
        assert screen.btn_reload is not None

    def test_table_vorhanden(self, screen):
        assert screen.table is not None


# ===========================================================================
# SCREEN 4: NewJetScreen – Formular-Aufbau + Pflichtfeld-Validierung
# ===========================================================================

class TestNewJetScreenWidgets:
    """Editor-Typen und Widget-Präsenz."""

    @pytest.fixture
    def screen(self, qtbot):
        from ui.screen_new_jet import NewJetScreen
        # fk_maps-Key muss _canon(col) sein (lowercase), Wert braucht 'name_to_id'
        fk_maps = {
            "rohling_fk": {
                "id2name": {1: "Rohling A", 2: "Rohling B"},
                "name_to_id": {"Rohling A": 1, "Rohling B": 2},
            }
        }
        w = NewJetScreen(
            columns=["ID", "Jet", "AirPressure", "StandardJet", "Rohling_FK"],
            fk_maps=fk_maps,
            bool_columns={"StandardJet"},
            id_column="ID",
            on_back_home=lambda: None,
            on_save=lambda data: 99,
        )
        qtbot.addWidget(w)
        w.show()
        return w

    def test_btn_save_vorhanden(self, screen):
        assert screen.btn_save is not None

    def test_btn_cancel_vorhanden(self, screen):
        assert screen.btn_cancel is not None

    def test_editors_wurden_erstellt(self, screen):
        assert len(screen._editors) > 0

    def test_fk_spalte_hat_combobox(self, screen):
        from PySide6.QtWidgets import QComboBox
        assert isinstance(screen._editors.get("Rohling_FK"), QComboBox)

    def test_bool_spalte_hat_checkbox(self, screen):
        from PySide6.QtWidgets import QCheckBox
        assert isinstance(screen._editors.get("StandardJet"), QCheckBox)

    def test_text_spalte_hat_lineedit(self, screen):
        from PySide6.QtWidgets import QLineEdit
        assert isinstance(screen._editors.get("Jet"), QLineEdit)

    def test_fk_combobox_hat_eintraege(self, screen):
        combo = screen._editors.get("Rohling_FK")
        # 1 Leer-Eintrag + 2 Rohling-Einträge = 3
        assert combo.count() >= 2

    def test_id_spalte_nicht_in_editors(self, screen):
        # ID-Spalte wird nicht als editierbarer Editor angelegt
        assert "ID" not in screen._editors


class TestNewJetScreenValidierung:
    """Pflichtfeld 'Jet' muss ausgefüllt sein – leeres Feld verhindert Save."""

    @pytest.fixture
    def screen(self, qtbot):
        from ui.screen_new_jet import NewJetScreen
        self.saved_data = []
        w = NewJetScreen(
            columns=["ID", "Jet", "AirPressure"],
            fk_maps={},
            bool_columns=set(),
            id_column="ID",
            on_back_home=lambda: None,
            on_save=lambda data: self.saved_data.append(data) or 1,
            check_jet_name=lambda name: True,
        )
        qtbot.addWidget(w)
        w.show()
        return w

    def test_leeres_jet_feld_verhindert_save(self, screen):
        with patch("ui.screen_new_jet.QMessageBox") as mock_mb:
            mock_mb.warning = MagicMock()
            screen._on_click_save()
        assert len(self.saved_data) == 0

    def test_leeres_jet_feld_zeigt_warnung(self, screen):
        with patch("ui.screen_new_jet.QMessageBox") as mock_mb:
            mock_mb.warning = MagicMock()
            screen._on_click_save()
            mock_mb.warning.assert_called_once()

    def test_ausgefuelltes_jet_feld_ermoeglicht_save(self, screen):
        jet_editor = screen._editors.get("Jet")
        assert jet_editor is not None
        jet_editor.setText("Testjet-999")
        with patch("ui.screen_new_jet.QMessageBox") as mock_mb:
            mock_mb.warning = MagicMock()
            screen._on_click_save()
        mock_mb.warning.assert_not_called()