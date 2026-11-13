"""ui/air_network.py - Air Supply Network computing part (Qt-free since 2026-11-13, shared with the web)."""
import io
import json
import subprocess
import sys

from ui import air_network as an


def test_qt_free():
    code = "import sys, ui.air_network; sys.exit(any(m.startswith('PySide6') for m in sys.modules))"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0


def test_example_solve_and_summaries():
    g = an.example_network()
    assert len(g.nodes) == 9 and len(g.edges) == 8 and g.validate() == []
    s = an.source_summary(g)
    assert s["n_jets"] == 3 and s["req_p"] > 5.0 and s["status"] in ("ok", "low") and s["opcost"]["cost_chf"] > 0
    r = an.results_rows(g)
    assert r["n_segs"] == 3 and len(r["rows"]) == 3 and all(x["status"] in ("ok", "velocity", "dp") for x in r["rows"])
    jet = next(n for n in g.nodes.values() if n.kind == an.NODE_JET)
    v = an.node_view(jet)
    assert "sufficient" in v and v["flow_nl_min"] > 0


def test_json_round_trip_and_db_jet():
    g = an.example_network()
    raw = json.loads(g.to_json())
    raw["nodes"][-1]["nozzle_db_jet_id"] = 7
    g2 = an.NetworkGraph.from_json(json.dumps(raw), {7: {"ID": 7, "Jet": "S315", "Luftbohrung": "1.1", "LuftlochAnzahl": 2}})
    j = g2.nodes[raw["nodes"][-1]["id"]]
    assert j.nozzle_db_jet["Jet"] == "S315" and j.label().startswith("S315")
    g2.solve()
    assert j.result_flow_nl_s > 0


def test_two_parents_warn_and_optimizer():
    g = an.example_network()
    ids = list(g.nodes)
    g.add_edge(ids[0], ids[-1])           # a jet with two incoming connections
    assert g.validate()
    opt, diffs = an.optimize_graph(an.example_network())
    assert all({"node_id", "param", "old_val", "new_val", "reason"} <= set(d) for d in diffs)
    c = an.cost_compare(an.example_network(), opt, an.OPCOST_DEFAULTS)
    assert c["current"] is not None and "savings" in c


def test_reports_to_memory():
    g = an.example_network()
    b = io.BytesIO()
    an.generate_pdf(b, g, "Test", "me", opt_diffs=an.optimize_graph(g)[1])
    assert b.getvalue()[:4] == b"%PDF"
    x = io.BytesIO()
    an.generate_excel(x, g, "Test")
    assert x.getvalue()[:2] == b"PK"
