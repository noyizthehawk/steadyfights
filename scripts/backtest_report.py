"""Train Bout Brain once and print its hold-out record, for comparing scoring
experiments on the scoring-overhaul branch.

    .venv/bin/python scripts/backtest_report.py [label]

The record is the newest 20% of fights, which the model never trains on —
the same figures the /bout-brain/record page shows.
"""
import contextlib
import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from part_2 import Prediction_model as pm  # noqa: E402

label = sys.argv[1] if len(sys.argv) > 1 else "run"

start = time.time()
with contextlib.redirect_stdout(io.StringIO()):   # train() prints a lot
    pm.train()
bt = pm.backtest

print(f"\n=== BOUT BRAIN BACKTEST · {label} ===")
print(f"hold-out fights : {bt['fights']}  ({bt['from']} → {bt['to']}, {bt['events']} events)")
print(f"trained on      : {bt['trained_on']} fights")
print(f"OVERALL         : {bt['accuracy']}%")
c = bt["confident"]
print(f"CONFIDENT (70+) : {c['accuracy']}%  on {c['fights']} picks")
print("\nscore band   picks  correct  accuracy")
for b in bt["bands"]:
    acc = f"{b['accuracy']}%" if b["accuracy"] is not None else "—"
    print(f"{b['label']:>10}  {b['picks']:>6}  {b['correct']:>7}  {acc:>8}")
print(f"\n({time.time() - start:.0f}s)")
