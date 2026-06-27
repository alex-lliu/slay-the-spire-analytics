"""
analysis/boss_floor_hp.py -- HP on entering each boss floor, and whether it predicts win/loss

current_hp_per_floor is 0-indexed: index i = HP after floor i+1.
So HP entering boss floor N = hp[N-2] (HP after the preceding floor).

Boss floors: 17 (act 1), 34 (act 2), 51 (act 3).

Usage:
    python -m analysis.boss_floor_hp
"""

import json
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = Path(os.getenv("DB_PATH", "sts.db"))

BOSSES = [
    ("Act 1 boss", 17, 17),
    ("Act 2 boss", 34, 34),
    # act 3 boss is on floor 50; wins record floor_reached=51, losses record 50
    ("Act 3 boss", 50, 50),
]


def boss_floor_hp(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT run_id, victory, floor_reached, current_hp_per_floor, max_hp_per_floor FROM runs"
    ).fetchall()

    for label, boss_floor, min_floor in BOSSES:
        idx = boss_floor - 2  # hp after the floor before the boss

        reached = [(v, json.loads(hp), json.loads(mhp))
                   for _, v, fr, hp, mhp in rows
                   if fr >= min_floor]

        if not reached:
            print(f"{label} (floor {boss_floor}): no runs reached this floor\n")
            continue

        wins   = [(hp[idx], mhp[idx]) for v, hp, mhp in reached if v == 1 and len(hp) > idx]
        losses = [(hp[idx], mhp[idx]) for v, hp, mhp in reached if v == 0 and len(hp) > idx]

        def stats(pairs):
            if not pairs:
                return None, None, None
            hps = [hp for hp, _ in pairs]
            pcts = [round(hp / mhp * 100) for hp, mhp in pairs if mhp]
            return round(sum(hps) / len(hps), 1), round(sum(pcts) / len(pcts), 1), len(pairs)

        w_hp, w_pct, wn = stats(wins)
        l_hp, l_pct, ln = stats(losses)

        print(f"{label} (floor {boss_floor}) — {len(reached)} runs reached")
        print(f"  {'Outcome':<10} {'Runs':>5}  {'Avg HP':>6}  {'Avg HP%':>7}")
        print("  " + "-" * 33)
        if wn:
            print(f"  {'Win':<10} {wn:>5}  {w_hp:>6}  {w_pct:>6}%")
        if ln:
            print(f"  {'Loss':<10} {ln:>5}  {l_hp:>6}  {l_pct:>6}%")
        print()

        # HP buckets: does higher HP entering the boss mean higher win rate?
        all_pairs = [(hp[idx], mhp[idx], v)
                     for v, hp, mhp in reached
                     if len(hp) > idx and mhp[idx]]
        buckets = [("<25%", 0, 25), ("25-50%", 25, 50), ("50-75%", 50, 75), (">75%", 75, 101)]
        print(f"  Win rate by HP% entering boss:")
        print(f"  {'HP%':<10} {'Runs':>5}  {'Wins':>5}  {'Win%':>6}")
        print("  " + "-" * 30)
        for blabel, lo, hi in buckets:
            bucket = [(hp, v) for hp, mhp, v in all_pairs if lo <= hp / mhp * 100 < hi]
            if not bucket:
                continue
            bwins = sum(v for _, v in bucket)
            print(f"  {blabel:<10} {len(bucket):>5}  {bwins:>5}  {bwins/len(bucket)*100:>5.1f}%")
        print()


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    boss_floor_hp(conn)
    conn.close()
