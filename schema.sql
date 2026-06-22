-- Slay the Spire Analytics — SQLite Schema
-- Verified against two real .run files: A0 loss (floor 7) and A11 win (floor 51)
--
-- Design notes:
--   • floors are stored as INTEGER — STS emits floats in older runs (1.0 vs 1),
--     cast to int at ingest time
--   • potions_floor_usage is a list of floor numbers where a potion was used;
--     len() = potions_used_count
--   • SKIP card choices are normalised to NULL in card_choices.picked
--   • special_seed = 0 is equivalent to absent; stored as NULL
--   • boss_relics is a list of dicts {picked, not_picked} — stored as JSON text
--   • event_choices are not in a child table (low query value, complex schema);
--     stored as JSON text on runs

CREATE TABLE IF NOT EXISTS runs (
    -- Identity
    run_id          TEXT PRIMARY KEY,   -- from local_time e.g. "20260616004145"
    play_id         TEXT UNIQUE,        -- UUID; NULL if absent
    character       TEXT NOT NULL,      -- "IRONCLAD"
    ascension_level INTEGER NOT NULL,   -- 0–20; 0 = base game

    -- Outcome
    victory         INTEGER NOT NULL,   -- 1 won / 0 lost
    floor_reached   INTEGER NOT NULL,
    killed_by       TEXT,               -- NULL on victory

    -- Time
    playtime        INTEGER,            -- seconds
    local_time      TEXT,               -- "20260616004145"
    timestamp       INTEGER,            -- Unix epoch

    -- Score & economy
    score           INTEGER,
    gold            INTEGER,            -- gold at run end

    -- Run flags
    is_daily        INTEGER NOT NULL DEFAULT 0,
    is_trial        INTEGER NOT NULL DEFAULT 0,
    is_endless      INTEGER NOT NULL DEFAULT 0,
    chose_seed      INTEGER NOT NULL DEFAULT 0,
    is_ascension_mode INTEGER NOT NULL DEFAULT 0,

    -- Seeds & meta
    seed_played     TEXT,
    special_seed    TEXT,               -- NULL if 0 or absent (no special seed)
    neow_bonus      TEXT,
    neow_cost       TEXT,
    build_version   TEXT,

    -- Purges & shop
    items_purged    TEXT,               -- JSON array of purged card ids
    purchased_purges INTEGER NOT NULL DEFAULT 0,
    items_purchased TEXT,               -- JSON array of shop purchases
    item_purchase_floors TEXT,          -- JSON array of floors

    -- Final deck & relics (JSON arrays)
    master_deck     TEXT,
    relics          TEXT,               -- final relic list
    relics_obtained TEXT,               -- relics gained mid-run with floor info (JSON array of {floor, key})
    boss_relics     TEXT,               -- list of {picked, not_picked} dicts

    -- Per-floor arrays (JSON, index = floor - 1)
    current_hp_per_floor  TEXT,
    max_hp_per_floor      TEXT,
    gold_per_floor        TEXT,
    path_per_floor        TEXT,         -- includes null entries for boss floors

    -- Events (stored as JSON blob; low query value)
    event_choices   TEXT,

    -- Derived counters (computed at ingest)
    deck_size             INTEGER,
    relic_count           INTEGER,
    total_damage_taken    INTEGER,
    potions_obtained_count INTEGER,
    potions_used_count    INTEGER        -- len(potions_floor_usage)
);

-- One row per card reward screen
CREATE TABLE IF NOT EXISTS card_choices (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL REFERENCES runs(run_id),
    floor       INTEGER NOT NULL,       -- cast from float at ingest
    picked      TEXT,                   -- NULL = skipped ("SKIP" normalised to NULL)
    not_picked  TEXT NOT NULL           -- JSON array e.g. '["Body Slam","Pommel Strike"]'
);
CREATE INDEX IF NOT EXISTS idx_card_choices_run    ON card_choices(run_id);
CREATE INDEX IF NOT EXISTS idx_card_choices_picked ON card_choices(picked);

-- One row per enemy encounter
CREATE TABLE IF NOT EXISTS damage_taken (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id  TEXT NOT NULL REFERENCES runs(run_id),
    floor   INTEGER NOT NULL,           -- cast from float
    enemies TEXT NOT NULL,
    damage  INTEGER NOT NULL,           -- cast from float
    turns   INTEGER NOT NULL            -- cast from float
);
CREATE INDEX IF NOT EXISTS idx_damage_run     ON damage_taken(run_id);
CREATE INDEX IF NOT EXISTS idx_damage_enemies ON damage_taken(enemies);

-- One row per campfire visit
-- key: "REST" | "SMITH" | "LIFT" | "DIG" | "RECALL" | "TOKE"
-- data: card upgraded (SMITH), relic name (DIG/RECALL), NULL for REST
CREATE TABLE IF NOT EXISTS campfire_choices (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id  TEXT NOT NULL REFERENCES runs(run_id),
    floor   INTEGER NOT NULL,           -- cast from float
    key     TEXT NOT NULL,
    data    TEXT
);
CREATE INDEX IF NOT EXISTS idx_campfire_run ON campfire_choices(run_id);

-- One row per potion obtained
-- No per-potion used flag: see runs.potions_used_count for aggregate,
-- and runs.potions_floor_usage (stored on runs as JSON) for which floors
CREATE TABLE IF NOT EXISTS potions (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id  TEXT NOT NULL REFERENCES runs(run_id),
    potion  TEXT NOT NULL,
    floor   INTEGER NOT NULL            -- cast from float
);
CREATE INDEX IF NOT EXISTS idx_potions_run    ON potions(run_id);
CREATE INDEX IF NOT EXISTS idx_potions_potion ON potions(potion);
