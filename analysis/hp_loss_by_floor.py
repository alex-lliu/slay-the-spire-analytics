"""
analysis/hp_loss_by_floor.py -- which floor do you lose most HP on

Usage:
    python -m analysis.hp_loss_by_floor
"""

import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = Path(os.getenv("DB_PATH", "sts.db"))


def hp_loss_by_floor(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""
        SELECT
            floor,
            COUNT(*)                AS encounters,
            ROUND(AVG(damage), 1)   AS avg_damage,
            SUM(damage)             AS total_damage,
            MAX(damage)             AS max_damage
        FROM damage_taken
        WHERE damage > 0
        GROUP BY floor
        ORDER BY avg_damage DESC
        LIMIT 20
    """).fetchall()

    print("Top 20 floors by avg HP lost (only encounters where damage > 0)\n")
    print(f"  {'Floor':>5}  {'Encounters':>10}  {'Avg HP lost':>11}  {'Max':>4}  {'Total':>7}")
    print("  " + "-" * 47)
    for floor, enc, avg, total, mx in rows:
        print(f"  {floor:>5}  {enc:>10}  {avg:>11}  {mx:>4}  {total:>7}")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    hp_loss_by_floor(conn)
    conn.close()
