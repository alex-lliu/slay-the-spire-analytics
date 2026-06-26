"""
validate.py — sanity-check sts.db after each ingest

Usage:
    python validate.py
"""

import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = Path(os.getenv("DB_PATH", "sts.db"))

PASS = "  OK"
WARN = "WARN"
FAIL = "FAIL"


def check(label: str, passed: bool, detail: str = "", warn_only: bool = False) -> bool:
    status = PASS if passed else (WARN if warn_only else FAIL)
    line = f"[{status}] {label}"
    if detail:
        line += f" — {detail}"
    print(line)
    return passed or warn_only


def main() -> int:
    if not DB_PATH.exists():
        print(f"[{FAIL}] Database not found: {DB_PATH}")
        return 1

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    failures = 0

    def require(label: str, passed: bool, detail: str = "", warn_only: bool = False):
        nonlocal failures
        ok = check(label, passed, detail, warn_only)
        if not ok:
            failures += 1

    # ── row counts ────────────────────────────────────────────────────────────
    print("\n── Row counts ──────────────────────────────────────────────────────")
    counts = {}
    for table in ["runs", "card_choices", "damage_taken", "campfire_choices", "potions"]:
        n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        counts[table] = n
        print(f"  {table}: {n}")

    require("runs table non-empty", counts["runs"] > 0)
    require("child tables non-empty", all(counts[t] > 0 for t in ["card_choices", "damage_taken", "campfire_choices", "potions"]))

    # ── required field nulls ──────────────────────────────────────────────────
    print("\n── Required fields ─────────────────────────────────────────────────")
    for col in ["character", "floor_reached", "victory", "ascension_level"]:
        n = cur.execute(f"SELECT COUNT(*) FROM runs WHERE {col} IS NULL").fetchone()[0]
        require(f"no NULL {col}", n == 0, f"{n} nulls found")

    # ── duplicate run_ids ─────────────────────────────────────────────────────
    print("\n── Integrity ───────────────────────────────────────────────────────")
    dups = cur.execute(
        "SELECT COUNT(*) FROM (SELECT run_id, COUNT(*) n FROM runs GROUP BY run_id HAVING n > 1)"
    ).fetchone()[0]
    require("no duplicate run_ids", dups == 0, f"{dups} duplicates")

    # ── orphan rows ───────────────────────────────────────────────────────────
    for table in ["card_choices", "damage_taken", "campfire_choices", "potions"]:
        orphans = cur.execute(
            f"SELECT COUNT(*) FROM {table} WHERE run_id NOT IN (SELECT run_id FROM runs)"
        ).fetchone()[0]
        require(f"no orphan rows in {table}", orphans == 0, f"{orphans} orphans")

    # ── 'SKIP' strings left in card_choices ───────────────────────────────────
    bad_skips = cur.execute("SELECT COUNT(*) FROM card_choices WHERE picked = 'SKIP'").fetchone()[0]
    require("SKIP normalised to NULL in card_choices", bad_skips == 0, f"{bad_skips} raw 'SKIP' strings remain")

    # ── floor sanity ──────────────────────────────────────────────────────────
    print("\n── Floor sanity ────────────────────────────────────────────────────")
    min_f, max_f, avg_f = cur.execute(
        "SELECT MIN(floor_reached), MAX(floor_reached), ROUND(AVG(floor_reached), 1) FROM runs"
    ).fetchone()
    print(f"  floor_reached: min={min_f}, max={max_f}, avg={avg_f}")
    require("max floor ≤ 56", max_f <= 56, f"max={max_f}")
    require("min floor ≥ 1", min_f >= 1, f"min={min_f}")

    # wins should only reach floor 51+ (act 3 boss)
    win_below_51 = cur.execute(
        "SELECT COUNT(*) FROM runs WHERE victory = 1 AND floor_reached < 51"
    ).fetchone()[0]
    require("all wins reach floor 51+", win_below_51 == 0, f"{win_below_51} wins below floor 51", warn_only=True)

    # ── runs with zero card choices ───────────────────────────────────────────
    print("\n── Edge cases ──────────────────────────────────────────────────────")
    no_cards = cur.execute(
        "SELECT run_id, floor_reached, killed_by FROM runs "
        "WHERE run_id NOT IN (SELECT run_id FROM card_choices)"
    ).fetchall()
    # runs with 0 card choices are only suspicious if they reached floor > 1
    suspicious = [r for r in no_cards if r[1] > 1]
    require(
        "runs with 0 card choices only died on floor 1",
        len(suspicious) == 0,
        f"{len(suspicious)} suspicious: {suspicious}" if suspicious else f"{len(no_cards)} floor-1 deaths (expected)",
        warn_only=len(suspicious) == 0,
    )

    # ── result ────────────────────────────────────────────────────────────────
    conn.close()
    total = counts["runs"]
    print()
    if failures == 0:
        print(f"All checks passed. ({total} runs in DB)")
        return 0
    else:
        print(f"{failures} check(s) FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
