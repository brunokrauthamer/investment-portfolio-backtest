"""Read-only validation of the acquired S&P 500 CSV and manifest pair."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from backend.src.internet_data_getter.sp500.storage import Sp500FileStore


data_root = Path("data")
store = Sp500FileStore(data_root)
csv_bytes = store.active_path.read_bytes()
manifest = json.loads(store.manifest_path.read_text(encoding="utf-8"))
observations = store._validate_pair(manifest, csv_bytes)
print(f"Rows: {len(observations)}")
print(f"Coverage: {observations[0].date.isoformat()} through {observations[-1].date.isoformat()}")
print(f"CSV bytes: {len(csv_bytes)}")
print(f"CSV SHA-256: {hashlib.sha256(csv_bytes).hexdigest()}")
