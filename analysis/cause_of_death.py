"""
analysis/cause_of_death.py -- most common causes of death

Usage:
    python -m analysis.cause_of_death
"""

import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = Path(os.getenv("DB_PATH", "sts.db"))


def cause_of_death(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    total_losses = cur.execute("SELECT COUNT(*) FROM runs WHERE victory = 0").fetchone()[0]
    print(f"Total losses: {total_losses}\n")

    print(f"{'Cause':<30} {'Deaths':>6}  {'%':>5}")
    print("-" * 45)
    for enemy, n in cur.execute("""
        SELECT killed_by, COUNT(*) as n
        FROM runs
        WHERE victory = 0
        GROUP BY killed_by
        ORDER BY n DESC
    """):
        label = enemy if enemy else "(unknown)"
        print(f"{label:<30} {n:>6}  {n/total_losses*100:>4.1f}%")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    cause_of_death(conn)
    conn.close()
