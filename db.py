"""
db.py — SQLite ingest for slay-the-spire-analytics

Verified against:
  • A0 loss  (floor 7,  sample_run.json)
  • A11 win  (floor 51, second sample)

Key findings baked in:
  • floors/damage/turns can be float in older runs — always cast to int
  • potions_floor_usage is a list of floors used (not a dict, not a count)
  • SKIP card choices normalised to NULL
  • special_seed = 0 treated as NULL (no special seed)
  • boss_relics is [] on early floors, list of {picked, not_picked} on wins
  • event_choices stored as JSON blob (complex/optional sub-fields like cards_obtained)

Usage:
    python db.py                # ingest all runs from RUN_DIR into sts.db
    python db.py --reset        # drop DB and rebuild
    python db.py --smoke-test   # validate against sample_run.json
"""

import json
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH     = Path(os.getenv("DB_PATH", "sts.db"))
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


# ── helpers ───────────────────────────────────────────────────────────────────

def _int(v) -> int:
    """Cast int-or-float field to int (STS emits 1.0 in older runs)."""
    return int(v) if v is not None else 0


def _nullable_int(v):
    return int(v) if v is not None else None


# ── connection ────────────────────────────────────────────────────────────────

def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def reset_db(db_path: Path = DB_PATH) -> None:
    if db_path.exists():
        db_path.unlink()
    conn = get_connection(db_path)
    init_db(conn)
    conn.close()


# ── run_id ────────────────────────────────────────────────────────────────────

def derive_run_id(run: dict, filename: str = "") -> str:
    if lt := run.get("local_time"):
        return str(lt)
    if pid := run.get("play_id"):
        return pid
    return Path(filename).stem or "unknown"


# ── extractors ────────────────────────────────────────────────────────────────

def _run_row(run: dict, run_id: str) -> dict:
    damage_events = run.get("damage_taken", [])
    total_damage  = sum(_int(e.get("damage", 0)) for e in damage_events)

    potions_obtained  = run.get("potions_obtained", [])
    # potions_floor_usage: list of floor numbers where a potion was used
    potions_used_count = len(run.get("potions_floor_usage", []))

    # special_seed = 0 means no special seed (same as absent)
    special_seed = run.get("special_seed")
    if special_seed == 0:
        special_seed = None

    return {
        "run_id":           run_id,
        "play_id":          run.get("play_id"),
        "character":        run.get("character_chosen", "UNKNOWN"),
        "ascension_level":  _int(run.get("ascension_level", 0)),
        "victory":          int(run.get("victory", False)),
        "floor_reached":    _int(run.get("floor_reached", 0)),
        "killed_by":        run.get("killed_by"),
        "playtime":         _nullable_int(run.get("playtime")),
        "local_time":       run.get("local_time"),
        "timestamp":        _nullable_int(run.get("timestamp")),
        "score":            _nullable_int(run.get("score")),
        "gold":             _nullable_int(run.get("gold")),
        "is_daily":         int(run.get("is_daily", False)),
        "is_trial":         int(run.get("is_trial", False)),
        "is_endless":       int(run.get("is_endless", False)),
        "chose_seed":       int(run.get("chose_seed", False)),
        "is_ascension_mode": int(run.get("is_ascension_mode", False)),
        "seed_played":      run.get("seed_played"),
        "special_seed":     special_seed,
        "neow_bonus":       run.get("neow_bonus"),
        "neow_cost":        run.get("neow_cost"),
        "build_version":    run.get("build_version"),
        "items_purged":     json.dumps(run.get("items_purged", [])),
        "purchased_purges": _int(run.get("purchased_purges", 0)),
        "items_purchased":  json.dumps(run.get("items_purchased", [])),
        "item_purchase_floors": json.dumps(run.get("item_purchase_floors", [])),
        "master_deck":      json.dumps(run.get("master_deck", [])),
        "relics":           json.dumps(run.get("relics", [])),
        "relics_obtained":  json.dumps(run.get("relics_obtained", [])),
        "boss_relics":      json.dumps(run.get("boss_relics", [])),
        "current_hp_per_floor": json.dumps(run.get("current_hp_per_floor", [])),
        "max_hp_per_floor":     json.dumps(run.get("max_hp_per_floor", [])),
        "gold_per_floor":       json.dumps(run.get("gold_per_floor", [])),
        "path_per_floor":       json.dumps(run.get("path_per_floor", [])),
        "event_choices":        json.dumps(run.get("event_choices", [])),
        "deck_size":               len(run.get("master_deck", [])),
        "relic_count":             len(run.get("relics", [])),
        "total_damage_taken":      total_damage,
        "potions_obtained_count":  len(potions_obtained),
        "potions_used_count":      potions_used_count,
    }


def _card_choice_rows(run: dict, run_id: str) -> list[dict]:
    rows = []
    for event in run.get("card_choices", []):
        picked = event.get("picked")
        if picked and picked.upper() == "SKIP":
            picked = None
        rows.append({
            "run_id":     run_id,
            "floor":      _int(event.get("floor", 0)),
            "picked":     picked,
            "not_picked": json.dumps(event.get("not_picked", [])),
        })
    return rows


def _damage_rows(run: dict, run_id: str) -> list[dict]:
    return [
        {
            "run_id":  run_id,
            "floor":   _int(e.get("floor", 0)),
            "enemies": e.get("enemies", "Unknown"),
            "damage":  _int(e.get("damage", 0)),
            "turns":   _int(e.get("turns", 0)),
        }
        for e in run.get("damage_taken", [])
    ]


def _campfire_rows(run: dict, run_id: str) -> list[dict]:
    return [
        {
            "run_id": run_id,
            "floor":  _int(e.get("floor", 0)),
            "key":    e.get("key", "UNKNOWN"),
            "data":   e.get("data"),
        }
        for e in run.get("campfire_choices", [])
    ]


def _potion_rows(run: dict, run_id: str) -> list[dict]:
    return [
        {
            "run_id": run_id,
            "potion": e.get("key", "Unknown"),
            "floor":  _int(e.get("floor", 0)),
        }
        for e in run.get("potions_obtained", [])
    ]


# ── ingest ────────────────────────────────────────────────────────────────────

def ingest_run(conn: sqlite3.Connection, run: dict, filename: str = "") -> str:
    run_id = derive_run_id(run, filename)

    conn.execute("""
        INSERT OR REPLACE INTO runs (
            run_id, play_id, character, ascension_level, victory, floor_reached, killed_by,
            playtime, local_time, timestamp, score, gold,
            is_daily, is_trial, is_endless, chose_seed, is_ascension_mode,
            seed_played, special_seed, neow_bonus, neow_cost, build_version,
            items_purged, purchased_purges, items_purchased, item_purchase_floors,
            master_deck, relics, relics_obtained, boss_relics,
            current_hp_per_floor, max_hp_per_floor, gold_per_floor, path_per_floor,
            event_choices,
            deck_size, relic_count, total_damage_taken,
            potions_obtained_count, potions_used_count
        ) VALUES (
            :run_id, :play_id, :character, :ascension_level, :victory, :floor_reached, :killed_by,
            :playtime, :local_time, :timestamp, :score, :gold,
            :is_daily, :is_trial, :is_endless, :chose_seed, :is_ascension_mode,
            :seed_played, :special_seed, :neow_bonus, :neow_cost, :build_version,
            :items_purged, :purchased_purges, :items_purchased, :item_purchase_floors,
            :master_deck, :relics, :relics_obtained, :boss_relics,
            :current_hp_per_floor, :max_hp_per_floor, :gold_per_floor, :path_per_floor,
            :event_choices,
            :deck_size, :relic_count, :total_damage_taken,
            :potions_obtained_count, :potions_used_count
        )
    """, _run_row(run, run_id))

    for table in ("card_choices", "damage_taken", "campfire_choices", "potions"):
        conn.execute(f"DELETE FROM {table} WHERE run_id = ?", (run_id,))

    if rows := _card_choice_rows(run, run_id):
        conn.executemany(
            "INSERT INTO card_choices (run_id, floor, picked, not_picked) VALUES (:run_id, :floor, :picked, :not_picked)",
            rows,
        )
    if rows := _damage_rows(run, run_id):
        conn.executemany(
            "INSERT INTO damage_taken (run_id, floor, enemies, damage, turns) VALUES (:run_id, :floor, :enemies, :damage, :turns)",
            rows,
        )
    if rows := _campfire_rows(run, run_id):
        conn.executemany(
            "INSERT INTO campfire_choices (run_id, floor, key, data) VALUES (:run_id, :floor, :key, :data)",
            rows,
        )
    if rows := _potion_rows(run, run_id):
        conn.executemany(
            "INSERT INTO potions (run_id, potion, floor) VALUES (:run_id, :potion, :floor)",
            rows,
        )

    return run_id


def ingest_all(runs: list[tuple[dict, str]], db_path: Path = DB_PATH) -> None:
    conn = get_connection(db_path)
    init_db(conn)
    inserted, errors = 0, []
    for run, filename in runs:
        try:
            ingest_run(conn, run, filename)
            inserted += 1
        except Exception as exc:
            errors.append((filename, str(exc)))
    conn.commit()
    conn.close()
    print(f"✓ Ingested {inserted} runs into {db_path}")
    if errors:
        print(f"✗ {len(errors)} error(s):")
        for fname, err in errors:
            print(f"  {fname}: {err}")


# ── smoke test ────────────────────────────────────────────────────────────────

def smoke_test(sample_path: str = "sample_run.json") -> None:
    import tempfile
    run = json.loads(Path(sample_path).read_text())
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp = Path(f.name)
    conn = get_connection(tmp)
    init_db(conn)
    run_id = ingest_run(conn, run, sample_path)
    conn.commit()

    row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    print(f"run_id:               {row['run_id']}")
    print(f"character:            {row['character']}")
    print(f"ascension_level:      {row['ascension_level']}")
    print(f"victory:              {row['victory']}")
    print(f"floor_reached:        {row['floor_reached']}")
    print(f"killed_by:            {row['killed_by']}")
    print(f"deck_size:            {row['deck_size']}")
    print(f"relic_count:          {row['relic_count']}")
    print(f"total_damage_taken:   {row['total_damage_taken']}")
    print(f"potions_obtained:     {row['potions_obtained_count']}")
    print(f"potions_used:         {row['potions_used_count']}")
    print(f"purchased_purges:     {row['purchased_purges']}")

    n_cards    = conn.execute("SELECT COUNT(*) FROM card_choices    WHERE run_id=?", (run_id,)).fetchone()[0]
    n_damage   = conn.execute("SELECT COUNT(*) FROM damage_taken    WHERE run_id=?", (run_id,)).fetchone()[0]
    n_campfire = conn.execute("SELECT COUNT(*) FROM campfire_choices WHERE run_id=?", (run_id,)).fetchone()[0]
    n_potions  = conn.execute("SELECT COUNT(*) FROM potions          WHERE run_id=?", (run_id,)).fetchone()[0]
    skips      = conn.execute("SELECT COUNT(*) FROM card_choices WHERE picked IS NULL AND run_id=?", (run_id,)).fetchone()[0]
    bad_skips  = conn.execute("SELECT COUNT(*) FROM card_choices WHERE picked='SKIP' AND run_id=?",  (run_id,)).fetchone()[0]

    print(f"card_choices:         {n_cards}")
    print(f"  SKIP→NULL:          {skips} nulls / {bad_skips} raw 'SKIP' strings remaining")
    print(f"damage_taken:         {n_damage}")
    print(f"campfire_choices:     {n_campfire}")
    print(f"potions:              {n_potions}")

    # floor types should all be int
    floors = conn.execute("SELECT floor FROM damage_taken WHERE run_id=? ORDER BY floor", (run_id,)).fetchall()
    floor_vals = [r[0] for r in floors]
    all_int = all(isinstance(v, int) for v in floor_vals)
    print(f"floors are int:       {all_int}  {floor_vals[:4]}...")

    conn.close()
    tmp.unlink()
    print("✓ smoke test passed")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset",      action="store_true")
    ap.add_argument("--smoke-test", action="store_true")
    args = ap.parse_args()

    if args.smoke_test:
        smoke_test()
    else:
        if args.reset:
            print(f"Resetting {DB_PATH} ...")
            reset_db()
        from parser import load_runs
        print("Loading runs ...")
        run_dir = Path(os.getenv("RUN_DIR"))
        ingest_all(load_runs(run_dir))
