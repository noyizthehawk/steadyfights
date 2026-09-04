"""One-off repair: re-pair r_name/b_name with the ids they belong to.

Rows scraped incrementally took their names from the ufcstats event listing
(winner-first) while every other field came from the fight detail page (corner
order), so a blue-corner win crossed each name onto the opponent's id, height,
reach, stance and per-fight stats. The ids are correct, so names are re-derived
from an id -> name map built off the untouched pre-2026 bulk import.
"""
import sys
import pandas as pd
from collections import Counter

path = sys.argv[1]
df = pd.read_csv(path, low_memory=False)
dates = pd.to_datetime(df["date"], errors="coerce")
trusted = dates < "2026-01-01"

# id -> name from the bulk import (verified: zero ids carry two different names)
name_of = {}
for i, n in list(zip(df.r_id[trusted], df.r_name[trusted])) + list(zip(df.b_id[trusted], df.b_name[trusted])):
    name_of.setdefault(i, Counter())[n] += 1
name_of = {i: c.most_common(1)[0][0] for i, c in name_of.items()}

suspect = df.index[~trusted]
fixed = ambiguous = 0
# Several passes: a row with one known fighter names the debutant by elimination,
# which in turn makes that debutant known for the rows that follow.
for _ in range(5):
    ambiguous = 0
    for idx in suspect:
        r_id, b_id = df.at[idx, "r_id"], df.at[idx, "b_id"]
        kr, kb = name_of.get(r_id), name_of.get(b_id)
        pair = {df.at[idx, "r_name"], df.at[idx, "b_name"]}
        if kr and not kb and len(pair) == 2:
            kb = (pair - {kr}).pop()
            name_of[b_id] = kb
        elif kb and not kr and len(pair) == 2:
            kr = (pair - {kb}).pop()
            name_of[r_id] = kr
        if not (kr and kb):
            ambiguous += 1
            continue
        if df.at[idx, "r_name"] != kr or df.at[idx, "b_name"] != kb:
            df.at[idx, "r_name"], df.at[idx, "b_name"] = kr, kb
            fixed += 1
        # winner holds the detail-page name, so it is already right; winner_id was
        # derived from the crossed names and has to be recomputed.
        w = df.at[idx, "winner"]
        df.at[idx, "winner_id"] = r_id if w == kr else (b_id if w == kb else None)

print(f"{path}: repaired {fixed} rows, {ambiguous} unresolved (both fighters debuting)")
df.to_csv(path, index=False)
