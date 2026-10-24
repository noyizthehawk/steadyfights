"""Bout Brain's advertised record must be honest: decided fights only, misses
kept, confidence measured on the side it picked.

Run:  .venv/bin/python -m pytest web/backend/tests/test_bout_brain_record.py
"""
import pandas as pd

from part_2.Prediction_model import _build_backtest


def _rows():
    return pd.DataFrame({
        "event_name_A": ["UFC 1", "UFC 1", "UFC 2", "UFC 2"],
        "date_A": ["2025-01-01", "2025-01-01", "2025-02-01", "2025-02-01"],
        "name_A": ["Al", "Cy", "Ed", "Gus"],
        "name_B": ["Bo", "Di", "Flo", "Hal"],
        "winner_A": ["Al", "Di", "Flo", None],     # last one: draw / no contest
    })


def test_record_counts_decided_fights_and_keeps_misses():
    # P(A wins): Al 0.8 (right), Cy 0.75 (wrong, Di won), Ed 0.3 -> picks Flo (right)
    rec = _build_backtest(_rows(), [0.8, 0.75, 0.3, 0.9], n_train=100)
    assert rec["fights"] == 3                       # the draw is dropped
    assert rec["accuracy"] == round(2 / 3 * 100, 1)
    assert rec["events"] == 2 and rec["trained_on"] == 100
    assert (rec["from"], rec["to"]) == ("2025-01-01", "2025-02-01")
    assert [p["correct"] for p in rec["picks"]].count(False) == 1   # the miss is shown


def test_confidence_is_for_the_picked_side():
    rec = _build_backtest(_rows(), [0.8, 0.75, 0.3, 0.9], n_train=100)
    flo = next(p for p in rec["picks"] if p["pick"] == "Flo")
    assert flo["confidence"] == 70                  # 1 - 0.3, not 30
    # 70%+ sure: Al (80, right), Cy (75, wrong), Flo (70, right)
    assert rec["confident"] == {"fights": 3, "accuracy": round(2 / 3 * 100, 1)}
    assert rec["picks"][0]["date"] == "2025-02-01"  # newest first


def test_by_event_groups_every_pick_newest_first():
    rec = _build_backtest(_rows(), [0.8, 0.75, 0.3, 0.9], n_train=100)
    assert [e["event"] for e in rec["by_event"]] == ["UFC 2", "UFC 1"]
    ufc1 = rec["by_event"][1]
    assert (ufc1["correct"], ufc1["fights"]) == (1, 2) and len(ufc1["picks"]) == 2
    assert rec["by_event"][0]["fights"] == 1          # UFC 2's draw isn't counted


def test_bands_cover_every_decided_fight_on_the_shown_score():
    # shown scores: Al 80, Cy 75, Flo 70 (the draw is dropped). 0.695 rounds to
    # 70 on the card, so it must count as 70+ too — no 69.6-vs-70 drift.
    rows = pd.concat([_rows(), pd.DataFrame({
        "event_name_A": ["UFC 3"], "date_A": ["2025-03-01"],
        "name_A": ["Ian"], "name_B": ["Jo"], "winner_A": ["Ian"]})], ignore_index=True)
    rec = _build_backtest(rows, [0.8, 0.75, 0.3, 0.9, 0.695], n_train=100)
    bands = {b["label"]: b for b in rec["bands"]}
    assert sum(b["picks"] for b in rec["bands"]) == rec["fights"] == 4
    assert (bands["70-79"]["picks"], bands["70-79"]["correct"]) == (3, 2)   # Cy 75 ✗, Flo 70 ✓, Ian 70 ✓
    assert (bands["80+"]["picks"], bands["80+"]["accuracy"]) == (1, 100.0)
    assert bands["50-59"]["accuracy"] is None                               # empty band
    assert rec["confident"]["fights"] == bands["70-79"]["picks"] + bands["80+"]["picks"]
