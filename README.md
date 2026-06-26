# Slay the Spire Run Analytics

A data pipeline and dashboard that parses, stores, and analyzes
personal Slay the Spire run history to surface strategic insights
and performance trends.

## Motivation

I wanted to understand my own gameplay patterns: which cards I
consistently skip, which enemies kill me most, and whether my
win rate is actually improving over time.

## Tech Stack

- Python: parsing and data processing
- SQLite: run data storage
- Streamlit: analytics dashboard (planned)

## Project Structure

```
parser.py       reads .run files from RUN_DIR and filters valid runs
db.py           ingests parsed runs into sts.db
validate.py     sanity-checks the database after each ingest
schema.sql      SQLite schema definition
```

## Usage

**Ingest runs:**
```
python db.py
```

**Reset and rebuild the database:**
```
python db.py --reset
```

**Validate the database:**
```
python validate.py
```

## Database Schema

| Table | Description |
|---|---|
| `runs` | One row per run, top-level fields |
| `card_choices` | One row per card offered per floor |
| `damage_taken` | One row per enemy encounter |
| `campfire_choices` | One row per rest stop |
| `potions` | Potions obtained per run |

## Configuration

Set these in a `.env` file:

```
RUN_DIR=path/to/your/SlayTheSpire/runs
DB_PATH=sts.db
```
