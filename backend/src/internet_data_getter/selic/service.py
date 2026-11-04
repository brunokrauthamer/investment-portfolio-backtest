"""Run the explicit Selic chart scrape and preserve a complete CSV."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .source import SourceError
from .storage import SelicFileStore


@dataclass
class AcquisitionReport:
    status: str = "failed"
    observations: int = 0
    first_date: str | None = None
    last_date: str | None = None
    sha256: str | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return self.status in {"saved", "updated", "unchanged"} and not self.errors


class SelicAcquisition:
    def __init__(self, client, store: SelicFileStore):
        self.client = client
        self.store = store

    def run(self, now: datetime | None = None) -> AcquisitionReport:
        report = AcquisitionReport()
        try:
            with self.store.lock():
                source = self.client.fetch()
                result = self.store.save_locked(source, now or datetime.now(timezone.utc))
            report.status = result["status"]
            report.sha256 = result["sha256"]
            report.observations = len(source.observations)
            report.first_date = source.observations[0].date.isoformat()
            report.last_date = source.observations[-1].date.isoformat()
        except Exception as exc:
            report.errors.append(str(exc))
        return report
