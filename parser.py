import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

run_dir = Path(os.getenv("RUN_DIR"))


def load_runs(run_dir: Path) -> list[dict]:
    """Load and return all valid Ironclad runs from the given directory."""
    runs = []
    for f in run_dir.glob('*.run'):
        data = json.loads(f.read_text())
        if is_valid_run(data):
            runs.append(data)
    return runs


def is_valid_run(data: dict) -> bool:
    """Filter out non-Ironclad runs and accidental starts."""
    if data.get('character_chosen') != 'IRONCLAD':
        return False
    if data.get('floor_reached', 0) == 0 and not data.get('damage_taken'):
        return False
    return True


def scan_keys(run_dir: Path) -> None:
    """Print universal and optional fields across all run files."""
    all_keys = [set(json.loads(f.read_text()).keys())
                for f in run_dir.glob('*.run')]
    universal = set.intersection(*all_keys)
    optional = set.union(*all_keys) - universal
    print("Universal fields:", sorted(universal))
    print("Optional fields:", sorted(optional))


if __name__ == "__main__":
    scan_keys(run_dir)
    runs = load_runs(run_dir)
    print(f"Loaded {len(runs)} valid runs")
    wins = sum(1 for r in runs if r.get('victory'))
    losses = len(runs) - wins
    print(f"Wins: {wins}, Losses: {losses}, Win rate: {wins/len(runs):.1%}")

    early = [r for r in runs if r.get('ascension_level', 0) <= 3]
    recent = [r for r in runs if r.get('ascension_level', 0) >= 7]

    early_wr = sum(1 for r in early if r.get('victory')) / len(early)
    recent_wr = sum(1 for r in recent if r.get('victory')) / len(recent)

    print(f"Early runs (A0-A3): {len(early)} runs, {early_wr:.1%} win rate")
    print(f"Recent runs (A7+): {len(recent)} runs, {recent_wr:.1%} win rate")