"""db/series_conclusion.py + desktop Conclusion tab. dev_local; the conclusion written on a real series is deleted
again (with its change-log rows and notifications)."""
import os

os.environ.setdefault("TRIPPLET_MODE", "dev_local")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from db import series_conclusion as sc  # noqa: E402
from db.connection import execute, fetch_all  # noqa: E402

pytestmark = pytest.mark.skipif(not sc.table_ready(), reason="tblSeriesConclusion missing")


def _series_with_request():
    rows = fetch_all("SELECT ts.ID, er.CreatedBy FROM tblTrialSeries ts JOIN tblExperimente e ON e.ID = ts.ExperimentID "
                     "JOIN tblExperimentRequests er ON er.ID = e.ExperimentRequestID "
                     "LEFT JOIN tblSeriesConclusion c ON c.TrialSeriesID = ts.ID "
                     "WHERE c.ID IS NULL AND er.CreatedBy IS NOT NULL AND EXISTS (SELECT 1 FROM tblTrial t WHERE t.TrialSeriesID = ts.ID) "
                     "ORDER BY ts.ID DESC LIMIT 1")
    return rows[0] if rows else None


@pytest.fixture
def series():
    r = _series_with_request()
    if not r:
        pytest.skip("no series with an experiment request")
    sid = int(r["ID"])
    other = fetch_all("SELECT ID FROM tblUser WHERE ID <> ? ORDER BY ID LIMIT 1", [r["CreatedBy"]])[0]["ID"]
    yield sid, int(r["CreatedBy"]), int(other)
    sc.delete(sid)
    execute("DELETE FROM tblChangeLog WHERE SeriesID = ? AND Source = 'conclusion'", [sid])
    execute("DELETE FROM tblNotification WHERE TrialSeriesID = ? AND NotificationType = ?", [sid, sc.NOTIFICATION_TYPE])


def test_save_get_log_notify_search(series):
    sid, requester, actor = series
    user = {"id": actor, "access_level": 2}
    trial = fetch_all("SELECT ID FROM tblTrial WHERE TrialSeriesID = ? ORDER BY ID LIMIT 1", [sid])[0]["ID"]
    assert sc.get(sid)["request"] is not None and sc.missing_for_archive(sid)

    res = sc.save(sid, {"outcome": "partly", "summary": "Zzqx knot softer\nbut more air", "best_trials": [trial],
                        "findings": "Speed limit 900", "recommendation": "follow_up"}, user)
    assert res["created"] and res["notified"] == 1
    c = res["conclusion"]
    assert c["outcome"] == "partly" and c["summary"] == "Zzqx knot softer but more air" and c["best_trials"] == [int(trial)]
    assert not sc.missing_for_archive(sid)
    assert sc.summary_map([sid])[sid]["outcome"] == "partly"
    assert sid in sc.search(["zzqx", "softer"]) and sid not in sc.search(["zzqx", "nothere"])
    n = fetch_all("SELECT COUNT(*) AS n FROM tblNotification WHERE TrialSeriesID = ? AND RecipientUserID = ? "
                  "AND NotificationType = ?", [sid, requester, sc.NOTIFICATION_TYPE])[0]["n"]
    assert n == 1

    res2 = sc.save(sid, {**c, "outcome": "achieved"}, user)
    assert not res2["created"] and res2["notified"] == 0       # only the first save notifies
    log = fetch_all("SELECT FieldName, OldValue, NewValue FROM tblChangeLog WHERE SeriesID = ? AND Source = 'conclusion' "
                    "AND FieldName = 'Outcome' ORDER BY ID", [sid])
    assert [(r["OldValue"], r["NewValue"]) for r in log] == [(None, "partly"), ("partly", "achieved")]

    from db import quick_search
    hits = quick_search._search([], [], [], [], ["zzqx"])
    assert any(h["series_pk"] == sid for h in hits)


def test_rules(series):
    sid, _req, actor = series
    with pytest.raises(sc.ConclusionError) as e:
        sc.save(sid, {"summary": "x"}, {"id": actor, "access_level": 1})
    assert e.value.code == "no_right"
    with pytest.raises(sc.ConclusionError) as e:
        sc.save(sid, {"outcome": "great"}, {"id": actor, "access_level": 2})
    assert e.value.code == "invalid"
    with pytest.raises(sc.ConclusionError) as e:
        sc.save(sid, {"summary": "x" * 301}, {"id": actor, "access_level": 2})
    assert e.value.code == "too_long"
    foreign = fetch_all("SELECT ID FROM tblTrial WHERE TrialSeriesID <> ? LIMIT 1", [sid])[0]["ID"]
    with pytest.raises(sc.ConclusionError) as e:
        sc.save(sid, {"best_trials": [foreign]}, {"id": actor, "access_level": 2})
    assert e.value.code == "invalid"
    assert sc.save(sid, {}, {"id": actor, "access_level": 2})["created"] is False   # nothing to save


def test_desktop_tab(series, monkeypatch):
    sid, _req, actor = series
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    import app_meta
    monkeypatch.setattr(app_meta, "current_user", {"id": actor, "access_level": 2}, raising=False)
    from ui.widgets.conclusion_tab import ConclusionTab
    trials = [int(r["ID"]) for r in fetch_all("SELECT ID FROM tblTrial WHERE TrialSeriesID = ? ORDER BY ID", [sid])]
    tab = ConclusionTab()
    tab.load(sid, trials, [f"V{i + 1}" for i in range(len(trials))])
    assert not tab.is_dirty() and not tab._ed_goal.isVisible() and not tab.has_conclusion()
    tab._ed_summary.setText("Desktop tab test")
    tab._grp_outcome.buttons()[0].setChecked(True)
    tab._grp_outcome.buttons()[1].setChecked(True)           # exclusive: only the second stays
    tab._trial_boxes[0].setChecked(True)
    assert tab.is_dirty() and tab.current()["outcome"] == sc.OUTCOMES[1]
    assert tab.save() and not tab.is_dirty() and tab.has_conclusion()
    assert sc.get(sid)["best_trials"] == [trials[0]]


def test_report_block_slot_and_pdf(series):
    """Conclusion block of the series Report: for_report/report_text, the page slot, the PDF section."""
    import json
    from db import report_service as rs
    sid, _requester, actor = series
    trial = fetch_all("SELECT ID, Versuchsnummer FROM tblTrial WHERE TrialSeriesID = ? ORDER BY ID LIMIT 1", [sid])[0]
    other = fetch_all("SELECT ts.ID FROM tblTrialSeries ts LEFT JOIN tblSeriesConclusion c ON c.TrialSeriesID = ts.ID "
                      "WHERE c.ID IS NULL AND ts.ID <> ? ORDER BY ts.ID DESC LIMIT 1", [sid])[0]["ID"]
    sc.save(sid, {"outcome": "achieved", "summary": "Qqrep <b>fine</b>", "best_trials": [trial["ID"]],
                  "findings": "Line1\nLine2", "recommendation": "release", "recommendation_text": "go"},
            {"id": actor, "access_level": 2})
    rep = sc.for_report([sid, other, sid, "x", -1, 999999999])
    assert [r["series_id"] for r in rep] == [sid, int(other)]           # order kept, junk/duplicates dropped
    a, b = rep
    assert a["exists"] and a["outcome_label"] == "Achieved" and a["best"] == [f"V{trial['Versuchsnummer']}"]
    assert a["goal_from_request"] and a["recommendation_label"] == "Release" and a["name"]
    assert not b["exists"] and sc.report_text(b) == "No conclusion yet."
    txt = sc.report_text(a)
    assert "Outcome: Achieved" in txt and "Best trials: V" in txt and "Recommendation: Release – go" in txt

    recv, args = rs.handle("loadConclusions", [json.dumps([sid])], user={"id": actor}, series_pk=sid)
    assert recv == "receiveConclusions" and args[1] is True and args[0][0]["summary"] == "Qqrep <b>fine</b>"

    pdf = rs.build_report_pdf({"reportTitle": "t", "author": "a", "sourceType": "Trial Series", "globalNote": "",
                               "conclusionSeries": [sid], "showInfobox": False, "infobox": {}, "charts": []})
    assert pdf[:4] == b"%PDF"


def test_report_page_has_conclusion_button():
    from ui.report_html_template import _HTML_TEMPLATE
    assert 'id="btn-conclusion"' in _HTML_TEMPLATE and "function receiveConclusions" in _HTML_TEMPLATE
    assert "showConclusion: _showConclusion" in _HTML_TEMPLATE and "conclusionSeries:" in _HTML_TEMPLATE
