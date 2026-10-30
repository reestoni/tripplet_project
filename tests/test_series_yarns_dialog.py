"""Yarns of a series (ui/series_yarns_dialog.py): diff -> operations, summary,
series rule "a yarn keeps its ply number", yarn search. Pure logic, no database."""
import copy

import pytest

pytest.importorskip("PySide6")

from ui.series_yarns_dialog import (
    PlyRow, State, describe, duplicate_rows, filter_yarns, mixed_plies, next_ply_label, plan, ply_of_yarn,
    trials_without_ply,
)

TRIALS = [(1, 1, "V1"), (2, 2, "V2"), (3, 3, "V3")]
USES = {1: "Core", 2: "Effect"}


def _state():
    return State(list(TRIALS), [
        PlyRow("Ply 1", 10, "PES 167", 1, {1: 1, 2: 1, 3: 1}, 10, 1),
        PlyRow("Ply 2", 20, "PA 78", None, {1: 1, 3: 1}, 20, None),
    ])


def test_no_change_no_ops():
    st = _state()
    assert plan(st, copy.deepcopy(st)) == []


def test_change_yarn_matches_the_loaded_row():
    before = _state()
    after = copy.deepcopy(before)
    after.rows[1].yarn_id, after.rows[1].yarn_name = 30, "PA 44"
    ops = plan(before, after)
    assert len(ops) == 1
    o = ops[0]
    assert (o["op"], o["match"], o["trials"], o["new_yarn"], o["yarn_changed"], o["use_changed"]) == (
        "change", ("Ply 2", 20, None), [1, 3], 30, True, False)
    assert describe(ops, USES) == ["Ply 2: PA 78 → PA 44 (2 trials)"]


def test_change_use_only():
    before = _state()
    after = copy.deepcopy(before)
    after.rows[0].use_id = 2
    ops = plan(before, after)
    assert ops[0]["match"] == ("Ply 1", 10, 1) and ops[0]["new_use"] == 2 and not ops[0]["yarn_changed"]
    assert describe(ops, USES) == ["Ply 1 (PES 167): use Core → Effect (3 trials)"]


def test_ends_and_on_off():
    before = _state()
    after = copy.deepcopy(before)
    after.rows[0].ends[2] = 3      # 1 -> 3 ends
    after.rows[1].ends[3] = 0      # off
    after.rows[1].ends[2] = 1      # on
    ops = plan(before, after)
    kinds = sorted((o["op"], o.get("trial"), o.get("n")) for o in ops)
    assert kinds == [("add", 2, 1), ("add", 2, 2), ("remove", 3, 1)]
    text = describe(ops, USES)
    assert "Ply 1 (PES 167, Core) added to: V2 +2 ends" in text
    assert "Ply 2 (PA 78) added to: V2" in text
    assert "Ply 2 (PA 78) removed from: V3" in text


def test_new_yarn_takes_next_free_number():
    before = _state()
    after = copy.deepcopy(before)
    after.rows.append(PlyRow(next_ply_label(after.rows), 40, "EL 20", None, {1: 1, 2: 1, 3: 1}))
    assert after.rows[-1].ply == "Ply 3"
    ops = plan(before, after)
    assert [(o["op"], o["trial"], o["ply"], o["yarn"]) for o in ops] == [
        ("add", 1, "Ply 3", 40), ("add", 2, "Ply 3", 40), ("add", 3, "Ply 3", 40)]


def test_same_yarn_other_use_keeps_its_ply_number():
    st = _state()
    assert ply_of_yarn(st.rows, 10) == "Ply 1"      # series rule: PES 167 is Ply 1
    assert ply_of_yarn(st.rows, 99) is None
    st.rows.append(PlyRow("Ply 1", 10, "PES 167", 2, {1: 1}))   # same yarn as "Effect"
    assert mixed_plies(st.rows) == set()            # same yarn, other use: not "old data"
    assert duplicate_rows(st) == []
    st.rows[-1].use_id = 1                          # same use twice -> can't be told apart
    assert [r.use_id for r in duplicate_rows(st)] == [1]


def test_every_trial_keeps_a_ply():
    st = _state()
    st.rows[0].ends[2] = 0
    assert trials_without_ply(st) == ["V2"]


def test_mixed_old_data_is_detected():
    rows = [PlyRow("Ply 1", 10, "a"), PlyRow("Ply 1", 11, "b"), PlyRow("Ply 2", 12, "c")]
    assert mixed_plies(rows) == {"Ply 1"}


def test_yarn_search_all_words_any_order():
    yarns = [{"id": 1, "name": "PES 167f48 DTY", "search": "pes 167f48 dty polyester"},
             {"id": 2, "name": "PA 78f68", "search": "pa 78f68 polyamide"}]
    assert [y["id"] for y in filter_yarns(yarns, "dty 167")] == [1]
    assert [y["id"] for y in filter_yarns(yarns, "")] == [1, 2]
    assert filter_yarns(yarns, "167 pa") == []


def test_reference_samples_may_have_no_yarn():
    st = _state()
    st.trials.append((4, -1, "Ref"))
    st.refs = {4}
    assert trials_without_ply(st) == []          # a reference without plies is fine
    st.rows[0].ends[2] = 0
    st.rows[1].ends[2] = 0
    assert trials_without_ply(st) == ["V2"]      # normal trials still need one
