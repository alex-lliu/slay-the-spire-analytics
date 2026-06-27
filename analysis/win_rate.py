"""
analysis/win_rate.py -- win rate overall and by character

Usage:
    python -m analysis.win_rate
"""

import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = Path(os.getenv("DB_PATH", "sts.db"))


def win_rate(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    total, wins = cur.execute(
        "SELECT COUNT(*), SUM(victory) FROM runs"
    ).fetchone()
    print(f"Overall: {wins}/{total} ({wins/total*100:.1f}%)")

    print("\nBy character:")
    for char, n, w in cur.execute(
        "SELECT character, COUNT(*), SUM(victory) FROM runs GROUP BY character ORDER BY COUNT(*) DESC"
    ):
        print(f"  {char}: {w}/{n} ({w/n*100:.1f}%)")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    win_rate(conn)
    conn.close()
