"""
analysis/campfire.py -- campfire rest vs upgrade decisions and their outcomes

Usage:
    python -m analysis.campfire
"""

import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = Path(os.getenv("DB_PATH", "sts.db"))


def campfire(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    # Overall choice distribution
    total_choices = cur.execute("SELECT COUNT(*) FROM campfire_choices").fetchone()[0]
    print(f"Total campfire choices: {total_choices}\n")

    print(f"  {'Choice':<10} {'Count':>5}  {'%':>5}")
    print("  " + "-" * 25)
    for key, n in cur.execute(
        "SELECT key, COUNT(*) FROM campfire_choices GROUP BY key ORDER BY 2 DESC"
    ):
        print(f"  {key:<10} {n:>5}  {n/total_choices*100:>4.1f}%")

    keys = [row[0] for row in cur.execute("SELECT DISTINCT key FROM campfire_choices ORDER BY key")]

    print("\nWin rate for runs that used each campfire action at least once:")
    print(f"  {'Choice':<10} {'Runs':>5}  {'Wins':>5}  {'Win%':>6}")
    print("  " + "-" * 32)
    for key in keys:
        n, wins = conn.execute("""
            SELECT COUNT(DISTINCT r.run_id), SUM(r.victory)
            FROM runs r
            WHERE EXISTS (
                SELECT 1 FROM campfire_choices c
                WHERE c.run_id = r.run_id AND c.key = ?
            )
        """, (key,)).fetchone()
        print(f"  {key:<10} {n:>5}  {wins:>5}  {wins/n*100:>5.1f}%")

    print("\nAvg campfire choices per run by outcome:")
    print(f"  {'Choice':<10} {'Losses avg':>10}  {'Wins avg':>8}")
    print("  " + "-" * 33)
    for key in keys:
        loss_avg = conn.execute("""
            SELECT ROUND(AVG(cnt), 2) FROM (
                SELECT COUNT(*) as cnt FROM campfire_choices c
                JOIN runs r ON c.run_id = r.run_id
                WHERE c.key = ? AND r.victory = 0
                GROUP BY c.run_id
            )
        """, (key,)).fetchone()[0]
        win_avg = conn.execute("""
            SELECT ROUND(AVG(cnt), 2) FROM (
                SELECT COUNT(*) as cnt FROM campfire_choices c
                JOIN runs r ON c.run_id = r.run_id
                WHERE c.key = ? AND r.victory = 1
                GROUP BY c.run_id
            )
        """, (key,)).fetchone()[0]
        print(f"  {key:<10} {str(loss_avg):>10}  {str(win_avg):>8}")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    campfire(conn)
    conn.close()
