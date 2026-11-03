"""Exercise a complete BCB scrape while keeping acquired bytes outside project data."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from backend.src.internet_data_getter.selic.service import SelicAcquisition
from backend.src.internet_data_getter.selic.source import SgsSelicClient
from backend.src.internet_data_getter.selic.storage import SelicFileStore


with tempfile.TemporaryDirectory(prefix="selic-live-smoke-") as temp:
    data_root = Path(temp) / "data"
    report = SelicAcquisition(SgsSelicClient(), SelicFileStore(data_root)).run()
    print(f"complete={report.complete}")
    print(f"status={report.status}")
    print(f"observations={report.observations}")
    print(f"first_date={report.first_date}")
    print(f"last_date={report.last_date}")
    print(f"sha256={report.sha256}")
    print(f"output_exists={ (data_root / 'selic/source/selic_sgs_11.csv').is_file() }")
    for error in report.errors:
        print(f"error={error}")
    if not report.complete:
        raise SystemExit(1)
