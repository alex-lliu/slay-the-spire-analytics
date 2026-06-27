"""
analysis/skip_correlation.py -- does skipping certain cards correlate with wins?

For each card, among runs where it was offered at least once, compare the win
rate of runs where you picked it vs runs where you skipped it every time.

Usage:
    python -m analysis.skip_correlation
"""

import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = Path(os.getenv("DB_PATH", "sts.db"))

MIN_RUNS = 10  # minimum runs offered to show a card


def skip_correlation(conn: sqlite3.Connection) -> None:
    # For each run+card, determine: was it ever picked, or always skipped?
    rows = conn.execute("""
        WITH card_offers AS (
            -- all (run_id, card) pairs where the card was offered
            SELECT run_id, picked AS card
            FROM card_choices
            WHERE picked IS NOT NULL AND picked != 'Singing Bowl'
            UNION ALL
            SELECT run_id, value AS card
            FROM card_choices, json_each(not_picked)
            WHERE value != 'Singing Bowl'
        ),
        run_card AS (
            -- for each (run, card): did the run ever pick this card from a reward?
            SELECT
                co.run_id,
                co.card,
                MAX(CASE WHEN cc.picked = co.card THEN 1 ELSE 0 END) AS picked_in_run
            FROM card_offers co
            JOIN card_choices cc ON cc.run_id = co.run_id
            GROUP BY co.run_id, co.card
        )
        SELECT
            rc.card,
            COUNT(DISTINCT rc.run_id)                                           AS runs_offered,
            SUM(CASE WHEN rc.picked_in_run = 0 THEN 1 ELSE 0 END)              AS runs_skipped,
            SUM(CASE WHEN rc.picked_in_run = 1 THEN 1 ELSE 0 END)              AS runs_picked,
            ROUND(AVG(CASE WHEN rc.picked_in_run = 0 THEN r.victory END)*100,1) AS skip_wr,
            ROUND(AVG(CASE WHEN rc.picked_in_run = 1 THEN r.victory END)*100,1) AS pick_wr
        FROM run_card rc
        JOIN runs r ON r.run_id = rc.run_id
        GROUP BY rc.card
        HAVING runs_offered >= ?
        ORDER BY (skip_wr - pick_wr) DESC
    """, (MIN_RUNS,)).fetchall()

    print(f"Skip vs pick win rate by card (min {MIN_RUNS} runs offered)\n")
    print(f"  {'Card':<30} {'Offered':>7}  {'Skip WR':>7}  {'Pick WR':>7}  {'Diff':>6}")
    print("  " + "-" * 63)

    print("  -- Skipping helps (positive diff) --")
    for card, offered, skipped, picked, skip_wr, pick_wr in rows:
        diff = (skip_wr or 0) - (pick_wr or 0)
        if diff <= 0:
            continue
        skip_str = f"{skip_wr}%" if skip_wr is not None else "  n/a"
        pick_str = f"{pick_wr}%" if pick_wr is not None else "  n/a"
        print(f"  {card:<30} {offered:>7}  {skip_str:>7}  {pick_str:>7}  {diff:>+5.1f}%")

    print("  -- Picking helps (negative diff) --")
    for card, offered, skipped, picked, skip_wr, pick_wr in reversed(rows):
        diff = (skip_wr or 0) - (pick_wr or 0)
        if diff >= 0:
            continue
        skip_str = f"{skip_wr}%" if skip_wr is not None else "  n/a"
        pick_str = f"{pick_wr}%" if pick_wr is not None else "  n/a"
        print(f"  {card:<30} {offered:>7}  {skip_str:>7}  {pick_str:>7}  {diff:>+5.1f}%")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    skip_correlation(conn)
    conn.close()
