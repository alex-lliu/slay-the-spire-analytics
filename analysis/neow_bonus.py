"""
analysis/neow_bonus.py -- win rate by Neow bonus chosen at the start of each run

Usage:
    python -m analysis.neow_bonus
"""

import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = Path(os.getenv("DB_PATH", "sts.db"))

MIN_RUNS = 3


def neow_bonus(conn: sqlite3.Connection) -> None:
    overall_wr = conn.execute("SELECT ROUND(AVG(victory)*100,1) FROM runs").fetchone()[0]

    rows = conn.execute("""
        SELECT
            neow_bonus,
            neow_cost,
            COUNT(*)                            AS runs,
            SUM(victory)                        AS wins,
            ROUND(AVG(victory) * 100, 1)        AS win_pct
        FROM runs
        WHERE neow_bonus IS NOT NULL
        GROUP BY neow_bonus, neow_cost
        HAVING runs >= ?
        ORDER BY win_pct DESC, runs DESC
    """, (MIN_RUNS,)).fetchall()

    print(f"Win rate by Neow bonus (min {MIN_RUNS} runs, overall WR: {overall_wr}%)\n")
    print(f"  {'Bonus':<40} {'Cost':<30} {'Runs':>5}  {'Wins':>5}  {'Win%':>6}  {'vs avg':>7}")
    print("  " + "-" * 97)
    for bonus, cost, runs, wins, win_pct in rows:
        cost_str = cost or ""
        diff = win_pct - overall_wr
        print(f"  {bonus:<40} {cost_str:<30} {runs:>5}  {wins:>5}  {win_pct:>5.1f}%  {diff:>+6.1f}%")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    neow_bonus(conn)
    conn.close()
