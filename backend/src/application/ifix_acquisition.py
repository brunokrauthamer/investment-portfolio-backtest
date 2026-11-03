"""Application orchestration for one explicit IFIX download run."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from backend.src.acquisition.ifix_source import available_years


@dataclass
class AcquisitionReport:
    saved: list[int] = field(default_factory=list)
    unchanged: list[int] = field(default_factory=list)
    updated: list[int] = field(default_factory=list)
    errors: dict[int | str, str] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return bool(self.saved or self.unchanged or self.updated) and not self.errors


class IfixAcquisition:
    """Coordinate source downloads, safe storage and the command result."""

    def __init__(self, client, store, current_year: int | None = None):
        self.client = client
        self.store = store
        self.current_year = current_year if current_year is not None else date.today().year

    def run(self, now: datetime | None = None) -> AcquisitionReport:
        timestamp = now or datetime.now(timezone.utc)
        report = AcquisitionReport()
        years = available_years(self.current_year)
        if not years:
            report.errors["discovery"] = "B3 offers no requested periods from 2011 onward"
            return report

        with self.store.lock():
            for year in years:
                try:
                    content = self.client.download_year(year)
                    result = self.store.save(year, content, timestamp)
                    getattr(report, result.status).append(year)
                except Exception as exc:
                    report.errors[year] = str(exc)
        return report
