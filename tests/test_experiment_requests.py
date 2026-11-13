"""db/experiment_requests.py + db/experiment_request_images.py - Experiment Requests
without Qt (shared with tripplet_web).

The before/after comparison against the desktop screens (form, load, popup, My
Requests list, the SQL of every save/status/assign path) and a real round trip ran
on dev_local. Here: Qt-free import, the pure rules, and the save decision tree
against a fake DB layer (no database needed)."""
import datetime
import os
import subprocess
import sys

import pytest

from db import experiment_requests as er
from db import experiment_request_images as ei

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

SU = {"id": 1, "username": "su", "access_level": 4}
NU = {"id": 12, "username": "nu", "access_level": 1}
OTHER = {"id": 2, "username": "other", "access_level": 2}

COLS = [er.ColumnInfo(n, None, t) for n, t in [
    ("ID", "int"), ("Timestamp", "datetime"), ("CreatedBy", "int"), ("Titel", "varchar(255)"),
    ("Versuchsgrund", "text"), ("Aufgabe", "text"), ("Beurteilungsparameter", "text"),
    ("Versuchsbedingungen", "text"), ("Wunschtermin", "date"), ("Projekt", "int"),
    ("MachineID", "int"), ("RequestStatus", "int"), ("DenialReason", "text"),
    ("ChangeOfRequestID", "int"), ("PriorVersionOfID", "int")]]
FIELDS = er.form_field_names(COLS)
FULL = {"Titel": "T", "Versuchsgrund": "g", "Aufgabe": "a", "Beurteilungsparameter": "b",
        "Versuchsbedingungen": "c", "Wunschtermin": datetime.date(2026, 1, 2), "Projekt": 5, "MachineID": None}


def test_imports_without_pyside6():
    env = dict(os.environ, TRIPPLET_MODE="dev_local")
    env.pop("QT_QPA_PLATFORM", None)
    r = subprocess.run([sys.executable, "-c",
                        "import sys; import db.experiment_requests, db.experiment_request_images, "
                        "db.experiment_request_changes; print('PySide6' in sys.modules)"],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "False"


# ---------------- fake DB ----------------

class _Cur:
    def __init__(self, log, rows):
        self.log, self.rows, self.lastrowid, self.rowcount, self.description = log, rows, 77, 1, None

    def execute(self, sql, params=None):
        if sql.strip().upper() in ("START TRANSACTION",):
            self.log.append(("<tx>", []))     # transaction marker, checked separately
            return
        self.log.append((" ".join(sql.split()), list(params or [])))

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        return []


class _Cn:
    def __init__(self, log, rows):
        self.log, self.rows = log, rows

    def cursor(self):
        return _Cur(self.log, self.rows)

    def commit(self):
        pass

    def rollback(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def fakedb(monkeypatch):
    log, calls = [], []
    monkeypatch.setattr(er, "get_connection", lambda: _Cn(log, []))
    monkeypatch.setattr(er.request_changes, "supports_change_tracking", lambda: True)
    monkeypatch.setattr(er.request_changes, "archive_current_version",
                        lambda rid: calls.append(("archive", rid)))
    # since 2026-11-13 the archive runs on the save's own cursor (one transaction)
    monkeypatch.setattr(er.request_changes, "supports_versioning", lambda: True)
    monkeypatch.setattr(er.request_changes, "_archive_current_version_on",
                        lambda cur, rid: calls.append(("archive", rid)))
    monkeypatch.setattr(er.request_changes, "create_or_update_pending_change",
                        lambda **kw: calls.append(("proposal", kw)) or 99)
    # default: an existing live request (status 1, owner 12) - not a draft
    monkeypatch.setattr(er, "fetch_request", lambda rid: {"ID": rid, "RequestStatus": 1, "CreatedBy": 12,
                                                          "ChangeOfRequestID": None, "PriorVersionOfID": None})
    return log, calls


def _save(user, rid, values, **kw):
    kw.setdefault("cols", COLS)
    kw.setdefault("field_names", FIELDS)
    return er.save_request(user, rid, values, **kw)


# ---------------- form / validation ----------------

def test_form_fields_types_and_order(monkeypatch):
    monkeypatch.setattr(er, "load_project_choices", lambda: [(5, "1 – P")])
    monkeypatch.setattr(er, "load_fk_choices", lambda name: [])
    f = er.form_fields(COLS)
    assert [x["name"] for x in f] == FIELDS
    kinds = {x["name"]: x["type"] for x in f}
    assert kinds == {"Titel": "text", "Versuchsgrund": "multiline", "Aufgabe": "multiline",
                     "Beurteilungsparameter": "multiline", "Versuchsbedingungen": "multiline",
                     "Wunschtermin": "date", "Projekt": "fk", "MachineID": "text"}
    assert [x["name"] for x in f if x["required"]] == [
        "Titel", "Versuchsgrund", "Aufgabe", "Beurteilungsparameter", "Versuchsbedingungen"]
    assert f[6]["choices"] == [(5, "1 – P")] and f[0]["choices"] is None


def test_validate_and_message():
    assert er.validate(FULL) == []
    v = dict(FULL, Aufgabe="   ", Titel=None)
    assert er.validate(v) == ["Titel", "Aufgabe"]
    assert "Still missing: Titel, Aufgabe" in er.missing_message(er.validate(v))
    # FVersuchsgrund spelling + case-insensitive field matching
    v = {k: x for k, x in FULL.items() if k != "Versuchsgrund"}
    assert er.validate(v) == ["Versuchsgrund"]
    v["FVersuchsgrund"] = "x"
    assert er.validate(v) == []
    assert er.find_key(["Titel_"], "titel") == "Titel_"
    assert er.find_key(["MachineID"], "Machine") == "MachineID"


def test_has_changes_and_coerce():
    assert er.has_changes(FULL, {}, FIELDS)
    assert not er.has_changes(dict(FULL, Titel=" T "), dict(FULL), FIELDS)
    assert not er.has_changes(dict(FULL, MachineID=""), dict(FULL), FIELDS)
    assert er.has_changes(dict(FULL, Aufgabe="b"), dict(FULL), FIELDS)
    c = er.coerce_values({"Titel": " x ", "Wunschtermin": "03.02.2026", "Aufgabe": "", "junk": 1}, COLS)
    assert list(c) == FIELDS and c["Titel"] == "x" and c["Aufgabe"] is None
    assert c["Wunschtermin"] == datetime.date(2026, 2, 3) and "junk" not in c


# ---------------- save decision tree ----------------

def test_save_insert(fakedb):
    log, calls = fakedb
    r = _save(NU, None, dict(FULL))
    assert r.kind == "inserted" and r.request_id == 77 and r.message == "Experiment request saved."
    sql, params = log[0]
    assert sql.startswith("INSERT INTO [tblExperimentRequests] ([Titel],[Versuchsgrund],[Aufgabe],"
                          "[Beurteilungsparameter],[Versuchsbedingungen],[Wunschtermin],[Projekt],"
                          "[Timestamp],[CreatedBy],[RequestStatus])")
    assert params[-2:] == [12, 1] and isinstance(params[-3], datetime.datetime)


def test_save_invalid_and_no_user(fakedb):
    log, _ = fakedb
    r = _save(NU, None, dict(FULL, Aufgabe=None))
    assert r.kind == "invalid" and r.missing == ["Aufgabe"] and r.title == "Missing information"
    assert _save({"id": None}, None, dict(FULL)).kind == "no_user"
    assert log == []


def test_save_unchanged_writes_nothing(fakedb):
    log, calls = fakedb
    r = _save(NU, 5, dict(FULL), loaded_values=dict(FULL), change_of_id=None)
    assert r.kind == "unchanged" and log == [] and calls == []


def test_save_superuser_archives_then_updates(fakedb):
    log, calls = fakedb
    r = _save(SU, 5, dict(FULL, Aufgabe="new"), loaded_values=dict(FULL), change_of_id=None)
    assert r.kind == "updated" and calls == [("archive", 5)]
    assert log.pop(0) == ("<tx>", [])           # archive + update in one transaction
    assert log[0][0] == ("UPDATE [tblExperimentRequests] SET [Titel]=?,[Versuchsgrund]=?,[Aufgabe]=?,"
                         "[Beurteilungsparameter]=?,[Versuchsbedingungen]=?,[Wunschtermin]=?,"
                         "[Projekt]=?,[MachineID]=? WHERE [ID]=?")
    assert log[0][1][2] == "new" and log[0][1][-1] == 5


def test_save_normal_user_makes_proposal(fakedb):
    log, calls = fakedb
    r = _save(NU, 5, dict(FULL, Aufgabe="new"), loaded_values=dict(FULL), change_of_id=None)
    assert r.kind == "proposal" and r.request_id == 99 and log == []
    kind, kw = calls[0]
    assert kind == "proposal" and kw["original_id"] == 5 and kw["created_by"] == 12
    assert list(kw["values"]) == FIELDS


def test_save_change_copy_updated_directly_without_archive(fakedb):
    log, calls = fakedb
    r = _save(NU, 9, dict(FULL, Aufgabe="new"), loaded_values=dict(FULL), change_of_id=5)
    assert r.kind == "updated" and calls == [] and log[-1][1][-1] == 9


def test_save_without_change_tracking_updates_directly(fakedb, monkeypatch):
    log, calls = fakedb
    monkeypatch.setattr(er.request_changes, "supports_change_tracking", lambda: False)
    r = _save(NU, 5, dict(FULL, Aufgabe="new"), loaded_values=dict(FULL), change_of_id=None)
    assert r.kind == "updated" and calls == [("archive", 5)]


def test_save_web_path_reads_row_and_checks_owner(fakedb, monkeypatch):
    log, calls = fakedb
    row = dict(FULL, ID=5, CreatedBy=12, ChangeOfRequestID=None, RequestStatus=1,
               Wunschtermin=datetime.datetime(2026, 1, 2))
    monkeypatch.setattr(er, "fetch_request", lambda rid: dict(row))
    assert _save(NU, 5, dict(FULL)).kind == "unchanged"     # datetime in DB == date in form
    with pytest.raises(PermissionError):
        _save(OTHER, 5, dict(FULL, Aufgabe="x"))
    assert _save(SU, 5, dict(FULL, Aufgabe="x")).kind == "updated"
    monkeypatch.setattr(er, "fetch_request", lambda rid: None)
    with pytest.raises(LookupError):
        _save(NU, 5, dict(FULL))


def test_create_draft_has_no_status(fakedb):
    log, _ = fakedb
    assert er.create_draft(NU, {"Titel": "d"}, COLS) == 77
    sql, params = log[0]
    assert "[RequestStatus]" not in sql and params[0] == "d" and params[-1] == 12
    with pytest.raises(RuntimeError):
        er.create_draft({"id": None}, {}, COLS)


# ---------------- permissions / status rules ----------------

def test_can_open_and_can_delete():
    row = {"CreatedBy": 12}
    assert er.can_open(NU, row) and er.can_open(SU, row) and not er.can_open(OTHER, row)
    assert not er.can_open(NU, None)
    img = {"CreatedBy": 12}
    assert ei.can_delete(NU, img) and ei.can_delete(SU, img) and not ei.can_delete(OTHER, img)
    assert not ei.can_delete(NU, {"CreatedBy": None})
    assert er.is_superuser(SU) and not er.is_superuser(NU) and not er.is_superuser({"access_level": "x"})


CHOICES = [(1, "Request"), (2, "Denied"), (3, "Approved"), (4, "Experiment")]


def test_check_status_change_rules():
    f = er.check_status_change
    assert f(CHOICES, 1, None)[0] == "invalid"
    assert f(CHOICES, 3, 4)[0] == "invalid"
    assert f(CHOICES, 3, 3)[0] == "same"
    assert f(CHOICES, 1, 2) == ("needs_reason", "Denied")
    assert f(CHOICES, 3, 1)[0] == "needs_confirmation"
    assert f(CHOICES, 4, 1)[0] == "needs_confirmation"
    assert f(CHOICES, 2, 1)[0] == "ok"
    assert f(CHOICES, 1, 3) == ("ok", "Approved")


def test_status_options():
    assert er.status_options(CHOICES, 3, True) == [("Request", 1, True), ("Denied", 2, True), ("Approved", 3, True)]
    assert er.status_options(CHOICES, 4, True)[-1] == ("Experiment", 4, False)
    assert er.status_options(CHOICES, 1, False)[0] == ("", None, True) and len(er.status_options(CHOICES, 1, False)) == 5


def test_superuser_only_actions_refuse_normal_users():
    with pytest.raises(PermissionError):
        er.set_status(NU, 1, 3)
    with pytest.raises(PermissionError):
        er.accept_pending_change(NU, 1)
    with pytest.raises(PermissionError):
        er.reject_pending_change(NU, 1, 2)
    with pytest.raises(PermissionError):
        er.assign_experiment(NU, 1, 2)


def test_list_helpers():
    assert er.list_columns(["ID", "Titel", "CreatedByUser", "Projekt", "ProjektText"], False) == [(1, "Titel"), (4, "ProjektText")]
    assert er.list_columns(["Titel", "CreatedByUser"], True) == [(0, "Titel"), (1, "CreatedByUser")]
    assert er.list_header_label("ProjektText") == "Project" and er.list_header_label("CreatedByUser") == "Owner"
    assert er.format_list_value("Wunschtermin", datetime.date(2026, 3, 4)) == "04.03.2026"
    assert er.format_list_value("Wunschtermin", "2026-03-04") == "04.03.2026"
    assert er.title_marker(True, True) == "⏳ " and er.title_marker(False, True) == "🆕 "
    assert er.is_new_unreviewed(1, False) and not er.is_new_unreviewed(1, True)
    assert er.status_tooltip(2, False, False, "why") == "Denial reason: why"


def test_display_and_banner():
    assert er.display_text("Wunschtermin", "2026-03-04 00:00:00") == "04.03.2026"
    assert er.display_text("Aufgabe", None) == ""
    assert er.denial_banner_text({"RequestStatus": 2, "DenialReason": "no"}) == "⚠ This request was denied.\nReason: no"
    assert er.denial_banner_text({"RequestStatus": 3, "DenialReason": "no"}) is None
    assert er.popup_title({"Titel": "a<b"}, 5, "V1 — ") == ("V1 — a<b", "V1 — <b>a&lt;b</b>")
    assert er.popup_title({"Titel": " "}, 5) == ("Experiment Request #5", "Experiment Request <b>#5</b>")
    rows = er.display_fields(COLS, {"Aufgabe": "x"})
    assert [r["label"] for r in rows][:2] == ["Created By", "Versuchsgrund"]
    assert "Titel" not in [r["name"] for r in rows] and "RequestStatus" not in [r["name"] for r in rows]


# ---------------- images ----------------

def test_new_original_filename():
    img = {"OriginalFilename": "photo.JPG", "StoredFilename": "abc.jpg"}
    assert ei.new_original_filename(img, "  new.png ") == "new.JPG"
    assert ei.new_original_filename(img, "a/b\\c") == "a_b_c.JPG"
    assert ei.new_original_filename(img, "   ") is None
    assert ei.new_original_filename(img, "17", prefix="V") == "V17.JPG"
    assert ei.new_original_filename(img, "v17", prefix="V") == "v17.JPG"
    assert ei.new_original_filename({"OriginalFilename": "x"}, "y", fallback_ext=".png") == "y.png"


def test_image_paths_and_download_root(tmp_path, monkeypatch):
    assert ei.relative_path_for_db(7) == ei.REQUEST_IMAGES_BASE_DIR + "\\7\\"
    assert ei.images_dir(7) == os.path.join(ei.REQUEST_IMAGES_BASE_DIR, "7")
    root = tmp_path / "imgs"
    (root / "7").mkdir(parents=True)
    good = root / "7" / "a.png"
    good.write_bytes(b"x")
    outside = tmp_path / "secret.txt"
    outside.write_text("no")
    monkeypatch.setattr(ei, "REQUEST_IMAGES_BASE_DIR", str(root))
    rows = [{"ID": 1, "FullPath": str(good)}, {"ID": 2, "FullPath": str(outside)},
            {"ID": 3, "FullPath": str(root / "7" / ".." / ".." / "secret.txt")}]
    monkeypatch.setattr(ei, "list_images", lambda rid: rows)
    assert ei.image_file(7, 1) == os.path.normcase(os.path.realpath(str(good)))
    assert ei.image_file(7, 2) is None and ei.image_file(7, 3) is None and ei.image_file(7, 9) is None


def test_rename_image_only_uploader_or_superuser(monkeypatch):
    """2026-11-13: same rule as delete (before: anyone who could open the request)."""
    import pytest
    from db import experiment_request_images as ei
    from db import experiment_requests as er
    monkeypatch.setattr(er, "fetch_request", lambda rid: {"ID": rid, "CreatedBy": 1})
    images = [{"ID": 3, "CreatedBy": 9, "OriginalFilename": "a.png", "StoredFilename": "x.png"}]
    monkeypatch.setattr(ei, "list_images", lambda rid: images)
    monkeypatch.setattr(ei, "persist_original_filename", lambda *a: True)
    with pytest.raises(PermissionError):
        ei.rename_image({"id": 1, "access_level": 2}, 4, 3, "new")       # owner of the request, not uploader
    assert ei.rename_image({"id": 1, "access_level": 4}, 4, 3, "new") == "new.png"   # superuser
    images[0]["CreatedBy"] = 1
    assert ei.rename_image({"id": 1, "access_level": 2}, 4, 3, "new") == "new.png"   # uploader


def test_save_finalises_draft_instead_of_proposal(fakedb, monkeypatch):
    """2026-11-13: a draft (images uploaded before the first save) becomes a normal request (status 1)."""
    log, calls = fakedb
    monkeypatch.setattr(er, "fetch_request", lambda rid: {"ID": rid, "RequestStatus": None, "CreatedBy": 12,
                                                          "ChangeOfRequestID": None, "PriorVersionOfID": None})
    r = _save(NU, 40, dict(FULL), loaded_values={}, change_of_id=None)
    assert r.kind == "inserted" and r.request_id == 40 and calls == []          # no proposal, no archive
    sql, params = log[-1]
    assert sql.startswith("UPDATE [tblExperimentRequests] SET [Titel]=?") and "[RequestStatus]=?" in sql
    assert params[-1] == 40 and params[-2] == 1 and params[-3] == 12
