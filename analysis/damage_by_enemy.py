"""
analysis/damage_by_enemy.py -- damage taken distribution by enemy

Usage:
    python -m analysis.damage_by_enemy
"""

import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = Path(os.getenv("DB_PATH", "sts.db"))

MIN_ENCOUNTERS = 5


def damage_by_enemy(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT
            enemies,
            COUNT(*)                        AS encounters,
            ROUND(AVG(damage), 1)           AS avg_damage,
            MIN(damage)                     AS min_damage,
            MAX(damage)                     AS max_damage,
            ROUND(AVG(turns), 1)            AS avg_turns
        FROM damage_taken
        GROUP BY enemies
        HAVING encounters >= ?
        ORDER BY avg_damage DESC
    """, (MIN_ENCOUNTERS,)).fetchall()

    print(f"Damage by enemy (min {MIN_ENCOUNTERS} encounters, sorted by avg damage)\n")
    print(f"  {'Enemy':<35} {'Enc':>4}  {'Avg':>5}  {'Min':>4}  {'Max':>4}  {'AvgTurns':>8}")
    print("  " + "-" * 67)
    for enemies, enc, avg, mn, mx, avg_turns in rows:
        print(f"  {enemies:<35} {enc:>4}  {avg:>5}  {mn:>4}  {mx:>4}  {avg_turns:>8}")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    damage_by_enemy(conn)
    conn.close()
