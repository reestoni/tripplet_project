"""clone_lab_rows_for_trial: a trial copy gets empty lab rows - measurements and
the measurement Timestamp are not copied (a copied Timestamp made YarnScope show
copies as "analysed"), tensions and foreign keys are kept."""
import datetime

import db.connection as dbc
from db import trial_actions


class _FakeCursor:
    def __init__(self, rows_by_table):
        self.rows_by_table = rows_by_table
        self.inserts = []
        self.description = None
        self._rows = []

    def execute(self, sql, params=()):
        if sql.startswith("SELECT"):
            table = sql.split(" FROM ")[1].split()[0]
            cols, rows = self.rows_by_table.get(table, ([], []))
            self.description = [(c,) for c in cols]
            self._rows = rows
        else:
            self.inserts.append((sql, list(params)))

    def fetchall(self):
        return self._rows


def test_copy_has_no_timestamp_and_no_measurements(monkeypatch):
    monkeypatch.setattr(dbc, "table_exists", lambda name: name == "tbllabordtyomat")
    ts = datetime.datetime(2026, 11, 18, 10, 35, 38)
    cols = ["ID", "TrialID", "GlobalID", "UserID", "Timestamp", "FPm", "kl_bin_1", "YarnTension"]
    cur = _FakeCursor({"tblLaborDTYoMat": (cols, [(1, 100, "g-old", 7, ts, 110.0, 12.9, 15.0)])})

    trial_actions.clone_lab_rows_for_trial(cur, 100, 200, current_uid=3)

    assert len(cur.inserts) == 1
    sql, params = cur.inserts[0]
    names = [c.strip(" []") for c in sql.split("(")[1].split(")")[0].split(",")]
    row = dict(zip(names, params))
    assert row["TrialID"] == 200
    assert row["Timestamp"] is None
    assert row["FPm"] is None and row["kl_bin_1"] is None
    assert row["YarnTension"] == 15.0
    assert row["UserID"] == 7
    assert row["GlobalID"] != "g-old"


def test_only_chosen_lab_tables_are_cloned(monkeypatch):
    monkeypatch.setattr(dbc, "table_exists", lambda name: name in ("tbllabortiter", "tbllabordtyomat"))
    cols = ["ID", "TrialID", "Timestamp", "FPm"]
    cur = _FakeCursor({"tbllabortiter": (cols, [(1, 100, None, 1.0)]),
                       "tblLaborDTYoMat": (cols, [(2, 100, None, 2.0)])})
    trial_actions.clone_lab_rows_for_trial(cur, 100, 200, tables=["TblLaborTiter"])
    assert len(cur.inserts) == 1 and "[tbllabortiter]" in cur.inserts[0][0]
    cur = _FakeCursor({"tbllabortiter": (cols, [(1, 100, None, 1.0)])})
    trial_actions.clone_lab_rows_for_trial(cur, 100, 200, tables=[])
    assert cur.inserts == []
