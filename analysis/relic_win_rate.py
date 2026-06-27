"""
analysis/relic_win_rate.py -- win rate in runs where each relic was held at end

Usage:
    python -m analysis.relic_win_rate
"""

import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = Path(os.getenv("DB_PATH", "sts.db"))

MIN_RUNS = 5  # ignore relics held in fewer than this many runs


def relic_win_rate(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""
        SELECT
            r.value                             AS relic,
            COUNT(*)                            AS runs,
            SUM(runs.victory)                   AS wins,
            ROUND(AVG(runs.victory) * 100, 1)   AS win_pct
        FROM runs, json_each(runs.relics) r
        GROUP BY relic
        HAVING runs >= ?
        ORDER BY win_pct DESC, runs DESC
    """, (MIN_RUNS,)).fetchall()

    overall_wr = conn.execute("SELECT ROUND(AVG(victory)*100,1) FROM runs").fetchone()[0]

    print(f"Win rate by relic held at end of run (min {MIN_RUNS} runs, overall WR: {overall_wr}%)\n")
    print(f"  {'Relic':<35} {'Runs':>5}  {'Wins':>5}  {'Win%':>6}  {'vs avg':>7}")
    print("  " + "-" * 63)
    for relic, runs, wins, win_pct in rows:
        diff = win_pct - overall_wr
        diff_str = f"{diff:+.1f}%"
        print(f"  {relic:<35} {runs:>5}  {wins:>5}  {win_pct:>5.1f}%  {diff_str:>7}")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    relic_win_rate(conn)
    conn.close()
