"""
analysis/card_picks.py -- cards always (or never) picked when offered

Usage:
    python -m analysis.card_picks
"""

import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = Path(os.getenv("DB_PATH", "sts.db"))

MIN_OFFERS = 5  # ignore cards offered fewer than this many times


def card_picks(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    # Count how many times each card was offered and how many times picked.
    # A card appears in not_picked (JSON array) every time it was offered but skipped.
    # picked IS NULL means the whole choice was skipped.
    rows = cur.execute("""
        WITH offers AS (
            -- each row is one card offer: the card that was picked
            SELECT picked AS card, 1 AS was_picked
            FROM card_choices
            WHERE picked IS NOT NULL AND picked != 'Singing Bowl'
            UNION ALL
            -- each element of not_picked is an offer that was declined
            SELECT value AS card, 0 AS was_picked
            FROM card_choices, json_each(not_picked)
            WHERE value != 'Singing Bowl'
        )
        SELECT
            card,
            COUNT(*)                        AS offers,
            SUM(was_picked)                 AS picks,
            ROUND(SUM(was_picked) * 100.0 / COUNT(*), 1) AS pick_pct
        FROM offers
        GROUP BY card
        HAVING offers >= ?
        ORDER BY pick_pct DESC, offers DESC
    """, (MIN_OFFERS,)).fetchall()

    print(f"\nAll cards (min {MIN_OFFERS} offers, by pick rate)")
    print(f"  {'Card':<35} {'Offers':>6}  {'Picks':>5}  {'Pick%':>6}")
    print("  " + "-" * 57)
    for card, offers, picks, pct in rows:
        print(f"  {card:<35} {offers:>6}  {picks:>5}  {pct:>5.1f}%")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    card_picks(conn)
    conn.close()
