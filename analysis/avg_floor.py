"""
analysis/avg_floor.py -- average floor reached on wins vs losses

Usage:
    python -m analysis.avg_floor
"""

import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = Path(os.getenv("DB_PATH", "sts.db"))


def avg_floor(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    for victory, label in [(1, "Wins"), (0, "Losses")]:
        n, avg = cur.execute(
            "SELECT COUNT(*), ROUND(AVG(floor_reached), 1) FROM runs WHERE victory = ?",
            (victory,)
        ).fetchone()
        print(f"{label} ({n} runs): avg floor {avg}")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    avg_floor(conn)
    conn.close()
