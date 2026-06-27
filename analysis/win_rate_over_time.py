"""
analysis/win_rate_over_time.py -- win rate over time (cumulative + rolling)

Usage:
    python -m analysis.win_rate_over_time
"""

import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = Path(os.getenv("DB_PATH", "sts.db"))

WINDOW = 20  # rolling window size


def win_rate_over_time(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""
        SELECT local_time, victory, ascension_level
        FROM runs
        WHERE local_time IS NOT NULL
        ORDER BY local_time ASC
    """).fetchall()

    total = len(rows)
    print(f"{total} runs ordered by date\n")

    # Cumulative win rate at each run
    wins = 0
    rolling = []
    print(f"  {'Run':>4}  {'Date':<16}  {'Asc':>3}  {'Result':<6}  {'Cumul WR':>9}  {'Rolling WR (last {})':>20}".format(WINDOW))
    print("  " + "-" * 70)

    for i, (ts, victory, asc) in enumerate(rows, 1):
        wins += victory
        cumul_wr = wins / i * 100
        rolling.append(victory)

        if len(rolling) > WINDOW:
            rolling.pop(0)
        roll_wr = sum(rolling) / len(rolling) * 100 if len(rolling) == WINDOW else None

        result = "WIN" if victory else "loss"
        date = str(ts)[:8]  # YYYYMMDD from local_time
        date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
        roll_str = f"{roll_wr:>6.1f}%" if roll_wr is not None else "      -"
        print(f"  {i:>4}  {date_fmt:<16}  A{asc:<2}  {result:<6}  {cumul_wr:>7.1f}%  {roll_str:>20}")

    print()
    # Summarise by quarters of the run history
    q = total // 4
    quarters = [
        ("First quarter",  rows[:q]),
        ("Second quarter", rows[q:2*q]),
        ("Third quarter",  rows[2*q:3*q]),
        ("Fourth quarter", rows[3*q:]),
    ]
    print("Win rate by quarter of run history:")
    print(f"  {'Period':<16} {'Runs':>5}  {'Wins':>5}  {'Win%':>6}")
    print("  " + "-" * 35)
    for label, chunk in quarters:
        w = sum(v for _, v, _ in chunk)
        print(f"  {label:<16} {len(chunk):>5}  {w:>5}  {w/len(chunk)*100:>5.1f}%")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    win_rate_over_time(conn)
    conn.close()
