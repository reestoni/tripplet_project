"""db/report_service.py - the Qt-free part of the series report (2026-11-13,
shared with the web app tripplet_web).

Verified when it was moved out of ui/screen_report.py: for 11 dev_local
series (HTML for a normal user and a superuser, with/without an initial
report), every read-only bridge slot, the save/fork/delete and layout
template round trips, the old and new JS sent to the page were
byte-identical (116 cases, ~14 MB); the PDF had the same pages, text and
images.

The DB tests run in a subprocess with TRIPPLET_MODE=dev_local (the mode of
db.connection is fixed at its first import - in the test process that may
be prod) and are skipped when the local DB cannot be reached.
"""
import json
import os
import subprocess
import sys
import textwrap

import pytest

from db import report_service as rs

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_dev_local(code: str) -> dict:
    """Run code in a fresh interpreter on dev_local; it must set `out` (dict)."""
    script = textwrap.dedent("""
        import os, sys, json
        os.environ["TRIPPLET_MODE"] = "dev_local"
        sys.path.insert(0, {root!r})
        from db import connection
        assert connection.is_dev_local_mode() and not connection.is_offline_mode()
        assert connection.current_db_name() == "tripplet_dev_local", connection.current_db_name()
        try:
            connection.fetch_all("SELECT 1 AS x")
        except Exception as e:
            print(json.dumps({{"__skip__": str(e)}})); sys.exit(0)
        from db import report_service as rs
        out = {{}}
    """).format(root=_ROOT) + textwrap.dedent(code) + "\nprint(json.dumps(out, default=str))\n"
    env = dict(os.environ, TRIPPLET_MODE="dev_local")
    env.pop("QT_QPA_PLATFORM", None)
    p = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                       cwd=_ROOT, env=env, timeout=300)
    assert p.returncode == 0, p.stderr[-3000:]
    res = json.loads(p.stdout.strip().splitlines()[-1])
    if "__skip__" in res:
        pytest.skip("dev_local not reachable: " + res["__skip__"])
    return res


# ---------------------------------------------------------------------------
# Without DB
# ---------------------------------------------------------------------------

def test_imports_without_pyside6():
    code = ("import os, sys; os.environ['TRIPPLET_MODE'] = 'dev_local'; "
            f"sys.path.insert(0, {_ROOT!r}); import db.report_service as r; "
            "r.build_report_pdf; r.series_report_html; "
            "print('PySide6' in sys.modules)")
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       cwd=_ROOT, timeout=120)
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == "False"


def test_screen_report_reexports():
    from ui import screen_report
    assert screen_report.advanced_filter_sql is rs.advanced_filter_sql
    assert screen_report.value_notes_text is rs.value_notes_text
    assert screen_report.MACHINE_JOIN == rs.MACHINE_JOIN


def test_js_call_format():
    # same text the desktop always sent
    assert rs.js_call("receiveQueryResult", [[], 0]) == "receiveQueryResult([], 0);"
    assert rs.js_call("receiveSaveResult", [None, False, "x", False]) == \
        'receiveSaveResult(null, false, "x", false);'
    assert rs.js_call("receiveLayoutTemplateSaved", [True, ""]) == 'receiveLayoutTemplateSaved(true,"");'
    assert rs.js_call("receiveLayoutTemplateDeleted", [False, 0]) == "receiveLayoutTemplateDeleted(false,0);"
    assert rs.js_call("receiveFreeFieldData", [2, "k", {5: 1.0}]) == \
        'receiveFreeFieldData(2, "k", {"5": 1.0});'


def test_superuser_rule():
    assert rs.is_superuser({"access_level": 4})
    assert rs.is_superuser({"access_level": "5"})
    assert not rs.is_superuser({"access_level": 3})
    assert not rs.is_superuser(None)
    assert not rs.is_superuser({"access_level": "x"})


def test_slot_errors_answer_the_page():
    # no DB involved: every one fails before the first query
    name, args = rs.handle("saveReport", ["{bad"], user={})
    assert name == "receiveSaveResult" and args[0] is None and args[1] is False and args[3] is False and args[2]
    assert rs.handle("runVisualQuery", ["not json", "jet", "[]", "[]"]) == ("receiveQueryResult", [[], 0])
    assert rs.handle("deleteLayoutTemplate", ["abc"]) == ("receiveLayoutTemplateDeleted", [False, 0])
    assert rs.handle("loadSeriesData", ["abc", "#fff"]) is None
    assert rs.handle("loadReport", ["abc"]) is None
    assert rs.handle("loadFreeField", ["tblTrial", "AirPressure", "", "1", "k"], series_pk=None) is None
    with pytest.raises(KeyError):
        rs.handle("exportPdf", ["{}"])                    # Qt-only, not a shared slot


def test_every_slot_has_a_receiver():
    for slot, (fn, receiver, kind) in rs.SLOTS.items():
        assert callable(fn) and receiver.startswith("receive") and kind in ("read", "write")


def test_value_notes_text():
    assert rs.value_notes_text([{"trial": "V7", "what": "Tenacity", "t": " odd ", "by": "Me", "at": "30.10.2026"},
                                {"trial": "V8", "what": "FP/m", "t": "x"}]) == \
        "V7 · Tenacity: odd (Me, 30.10.2026)\nV8 · FP/m: x"


def test_build_report_pdf(monkeypatch):
    import base64
    import datetime
    import ui.report_pdf_layout as lay
    monkeypatch.setattr(lay, "_load_pdf_template", lambda tid=None: dict(lay._PDF_TEMPLATE_DEFAULTS))
    # 1x1 PNG
    png = base64.b64encode(bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
        "0000000c4944415408d763f8ffff3f0005fe02fea7d6a4d80000000049454e44ae426082")).decode()
    payload = {"reportTitle": "Test <&> report", "author": "Me", "sourceType": "series", "reportId": 3,
               "infobox": {"seriesName": "S1"}, "showInfobox": True, "globalNote": "Summary",
               "charts": [{"title": "C1", "xLabel": "X", "yLabel": "Y", "b64": png},
                          {"title": "C2", "b64": png, "noteVisible": True, "noteText": "n"},
                          None,
                          {"title": "I", "blockType": "image", "imageWidth": "half", "b64": png},
                          {"title": "C3", "b64": png,
                           "valueNotes": [{"trial": "V1", "what": "T", "t": "note"}]}]}
    now = datetime.datetime(2026, 11, 13, 9, 30)
    pdf = rs.build_report_pdf(payload, now)
    assert pdf[:4] == b"%PDF" and len(pdf) > 2000
    assert rs.pdf_default_filename(payload, now) == "SmartChart_Test_report_20261113.pdf"
    try:
        import fitz
    except ImportError:
        return
    doc = fitz.open(stream=pdf, filetype="pdf")
    text = "".join(pg.get_text() for pg in doc)
    assert "Test <&> report" in text and "13.11.2026 09:30" in text
    assert "V1 · T: note" in text and "Notes on values" in text


# ---------------------------------------------------------------------------
# dev_local
# ---------------------------------------------------------------------------

def test_read_functions_on_dev_local():
    out = _run_dev_local("""
        from db.connection import fetch_all
        spk = int(fetch_all("SELECT TrialSeriesID AS s FROM tblTrial GROUP BY TrialSeriesID "
                            "ORDER BY COUNT(*) DESC LIMIT 1")[0]["s"])
        out["series_list"] = rs.series_list()[:3]
        d = rs.series_data(spk)
        out["series_data_keys"] = sorted(d)
        out["series_data_n"] = len(d["data"])
        out["series_data_meta"] = sorted(d["meta"])
        out["missing_series"] = rs.series_data(-987654)["name"]
        reports = rs.report_list()
        out["report_list"] = reports[:2]
        out["load_report"] = rs.load_report(reports[0]["id"]) if reports else None
        out["load_missing"] = rs.load_report(-1)
        out["layout_templates"] = rs.layout_templates()[:1]
        out["pdf_templates"] = rs.pdf_templates()
        page = rs.series_report_page(spk, None, {"username": "tester", "access_level": 4})
        html = page["html"]
        out["placeholders_left"] = [p for p in ("{data_json}", "{y_axes_json}", "{x_axes_json}",
                                                "{tbl_cols_json}", "{infobox_json}", "{primary_series_pk}",
                                                "{current_user_json}", "{is_superuser_json}",
                                                "{initial_report_id_json}") if p in html]
        other = rs.series_report_page(spk, 5, {"username": "x", "access_level": 1})["html"]
        out["html_vars"] = [s for h in (html, other) for s in
                            ('var CURRENT_USER  = "tester";', "var IS_SUPERUSER  = true;",
                             "var INITIAL_REPORT_ID = null;", 'var CURRENT_USER  = "x";',
                             "var IS_SUPERUSER  = false;", "var INITIAL_REPORT_ID = 5;") if s in h]
        out["page_counts"] = [page["n_trials"], page["n_refs"]]
        rows = rs.run_visual_query([spk], "jet", [], [])
        out["query_n"] = len(rows)
        out["query_keys"] = sorted(rows[0]) if rows else []
        vals = rs.free_field_values(spk, "tblTrial", "AirPressure", "")
        out["free"] = list(vals.items())[:2]
        out["free_unknown_table"] = rs.free_field_values(spk, "tblNoSuchTable", "X", "")
    """)
    assert out["series_list"] and set(out["series_list"][0]) == {"pk", "name"}
    assert out["series_data_keys"] == ["data", "meta", "name"] and out["series_data_n"] > 0
    assert out["series_data_meta"] == ["machine", "material"]
    assert out["missing_series"] == "Series -987654"
    if out["report_list"]:
        assert set(out["report_list"][0]) == {"id", "title", "author", "sourceType", "updated"}
        rep = out["load_report"]
        assert set(rep) == {"id", "title", "author", "sourceType", "seriesPK", "queryConfig",
                            "showInfobox", "infoboxPosition", "globalNote", "blocks"}
        assert isinstance(rep["blocks"], list) and isinstance(rep["queryConfig"], dict)
    assert out["load_missing"] is None
    for t in out["layout_templates"]:
        assert set(t) == {"id", "name", "description", "isDefault", "blocks"}
    assert out["pdf_templates"] and set(out["pdf_templates"][0]) == {"id", "name", "description", "isDefault"}
    assert out["placeholders_left"] == []
    assert out["html_vars"] == ['var CURRENT_USER  = "tester";', "var IS_SUPERUSER  = true;",
                                "var INITIAL_REPORT_ID = null;", 'var CURRENT_USER  = "x";',
                                "var IS_SUPERUSER  = false;", "var INITIAL_REPORT_ID = 5;"]
    assert out["page_counts"][0] > 0
    assert out["query_n"] > 0
    assert {"trial_id", "trial_nr", "air_pressure", "jet_name", "yarn_name", "machine_name"} <= set(out["query_keys"])
    assert out["free_unknown_table"] is None


def test_save_load_delete_round_trip_on_dev_local():
    out = _run_dev_local("""
        from db.connection import fetch_all, execute
        def counts():
            return [fetch_all(f"SELECT COUNT(*) AS n FROM {t}")[0]["n"]
                    for t in ("tblSmartChartReport", "tblSmartChartBlock", "tblSmartChartNote",
                              "tblSmartChartTemplate", "tblSmartChartTemplateBlock")]
        before = counts()
        created, tpl = [], None
        author = {"id": 900001, "username": "rt_author", "access_level": 1}
        other = {"id": 900002, "username": "rt_other", "access_level": 1}
        data = {"title": " RT report ", "author": " RT ", "sourceType": "series", "seriesPK": None,
                "queryConfig": {"k": [1, 2]}, "showInfobox": 0, "infoboxPosition": "right",
                "globalNote": " the note ",
                "blocks": [{"blockType": "chart", "sortOrder": 0, "chartIndex": 0, "xField": "air_pressure",
                            "yKey": "tenacity", "gridlinesY": "2", "gridlinesVisible": True},
                           {"blockType": "note", "sortOrder": 1, "noteTitle": "T", "noteText": "N",
                            "noteVisible": False}]}
        try:
            r = rs.save_report(data, author); created.append(r["id"])
            out["new"] = [r["forked"], r["message"]]
            rep = rs.load_report(r["id"])
            out["loaded"] = [rep["title"], rep["author"], rep["queryConfig"], rep["showInfobox"],
                             rep["infoboxPosition"], rep["globalNote"],
                             [(b["blockType"], b["xField"], b["noteVisible"], b["gridlinesVisible"])
                              for b in rep["blocks"]]]
            out["in_list"] = any(x["id"] == r["id"] for x in rs.report_list())
            # the author overwrites
            r2 = rs.save_report(dict(data, id=r["id"], title="RT changed", blocks=data["blocks"][:1]), author)
            out["update"] = [r2["id"] == r["id"], r2["forked"]]
            rep = rs.load_report(r["id"])
            out["updated"] = [rep["title"], len(rep["blocks"])]
            # somebody else gets an own copy, the original stays
            r3 = rs.save_report(dict(data, id=r["id"], title="RT fork"), other); created.append(r3["id"])
            out["fork"] = [r3["id"] != r["id"], r3["forked"], rs.load_report(r3["id"])["author"],
                           rs.load_report(r["id"])["title"]]
            # via the slot protocol (as page and bridge call it)
            res = rs.handle("deleteReport", [str(r3["id"])], user=other)
            out["delete_slot"] = res == ("receiveDeleteResult", [r3["id"]])
            created.remove(r3["id"])
            out["deleted"] = rs.load_report(r3["id"]) is None
            rs.delete_report(r["id"], author); created.remove(r["id"])
            # layout templates
            tpl = rs.save_layout_template({"name": "RT tpl", "createdBy": "rt",
                                           "blocks": [{"chartType": "scatter", "xKey": "a", "yKey": "b"}]})
            rs.overwrite_layout_template({"id": tpl, "name": "RT tpl 2", "blocks": [{}, {"xKey": "z"}]}, author)
            t = [x for x in rs.layout_templates() if x["id"] == tpl][0]
            out["tpl"] = [t["name"], [(b["chartType"], b["xKey"]) for b in t["blocks"]]]
            dflt = [x["id"] for x in rs.layout_templates() if x["isDefault"]]
            if dflt:
                out["tpl_default"] = [rs.handle("overwriteLayoutTemplate",
                                                [json.dumps({"id": dflt[0], "name": "x"})], user=author),
                                      rs.delete_layout_template(dflt[0])]
            out["tpl_deleted"] = rs.delete_layout_template(tpl); tpl = None
        finally:
            for x in created:
                execute("DELETE FROM tblSmartChartReport WHERE ID=?", [x])
            if tpl:
                execute("DELETE FROM tblSmartChartTemplate WHERE ID=?", [tpl])
        out["counts_equal"] = counts() == before
    """)
    assert out["new"] == [False, "Report saved successfully"]
    assert out["loaded"] == ["RT report", "RT", {"k": [1, 2]}, False, "right", "the note",
                             [["chart", "air_pressure", True, True], ["note", "", False, False]]]
    assert out["in_list"]
    assert out["update"] == [True, False] and out["updated"] == ["RT changed", 1]
    assert out["fork"] == [True, True, "rt_other", "RT changed"]
    assert out["delete_slot"] and out["deleted"]
    assert out["tpl"] == ["RT tpl 2", [["bar", ""], ["bar", "z"]]]
    if "tpl_default" in out:
        assert out["tpl_default"] == [["receiveLayoutTemplateSaved",
                                       [False, "Only superusers can edit the default template"]], False]
    assert out["tpl_deleted"] is True
    assert out["counts_equal"]


def test_delete_report_only_author_or_superuser(monkeypatch):
    """2026-11-13: same owner rule as overwriting - before, anybody could delete any report."""
    import db.connection as dbc
    owner = {"UserID": 7}
    monkeypatch.setattr(dbc, "fetch_all", lambda sql, p=None: [owner] if "SELECT UserID" in sql else [])
    deleted = []
    monkeypatch.setattr(dbc, "execute", lambda sql, p=None: deleted.append(p))
    assert rs.can_delete_report(5, {"id": 7, "access_level": 2})
    assert not rs.can_delete_report(5, {"id": 8, "access_level": 3})
    assert rs.can_delete_report(5, {"id": 8, "access_level": 4})
    owner["UserID"] = None
    assert rs.can_delete_report(5, {"id": 8, "access_level": 1})        # old report without owner stays free
    owner["UserID"] = 7
    receiver, args = rs.handle("deleteReport", ["5"], user={"id": 8, "access_level": 2}, series_pk=1)
    assert receiver == "receiveDeleteDenied" and not deleted
    receiver, args = rs.handle("deleteReport", ["5"], user={"id": 7, "access_level": 2}, series_pk=1)
    assert receiver == "receiveDeleteResult" and args == [5] and deleted


def test_group_join_keeps_table_and_uses_alias():
    """2026-11-13: the alias replaced the table name ("LEFT JOIN gb_x ON ...") - group-by 'rohling' always failed."""
    assert rs.group_join_sql("tblfoo", "gb_x", "LEFT JOIN tblfoo ON tblfoo.TrialID = T.ID") == \
        "LEFT JOIN tblfoo AS gb_x ON gb_x.TrialID = T.ID"
    # tbljetrohling has no JetID - the jet points to its blank (tbljets.Rohling)
    assert rs.group_join_sql("tbljetrohling", "gb_rohling", "LEFT JOIN tbljetrohling ON tbljetrohling.JetID = J.ID") == \
        "LEFT JOIN tbljetrohling AS gb_rohling ON gb_rohling.ID = J.Rohling"
