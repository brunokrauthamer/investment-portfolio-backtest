"""S&P 500 acquisition orchestration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from .source import DEFAULT_START_DATE, Observation, PageResult, SourceError, parse_date_bound
from .storage import Sp500FileStore, sha256

@dataclass
class AcquisitionReport:
    status: str = "failed"
    observations: int = 0
    first_date: str | None = None
    last_date: str | None = None
    sha256: str | None = None
    added: int = 0
    updated: int = 0
    requested_windows: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return self.status in {"saved", "updated", "unchanged"} and not self.errors


class Sp500Acquisition:
    def __init__(self, client, store: Sp500FileStore):
        self.client = client
        self.store = store

    @staticmethod
    def _windows(start: date, end: date, existing: tuple[Observation, ...]) -> list[tuple[date, date]]:
        if not existing:
            return [(start, end)]
        earliest, latest = existing[0].date, existing[-1].date
        windows: list[tuple[date, date]] = []
        if start < earliest:
            backfill_end = min(end, earliest - timedelta(days=1))
            if start <= backfill_end:
                windows.append((start, backfill_end))
        if end > latest:
            forward_start = latest if start <= latest else start
            windows.append((forward_start, end))
        elif start <= latest <= end and not any(left <= latest <= right for left, right in windows):
            windows.append((latest, latest))
        return windows

    @staticmethod
    def _merge(
        existing: tuple[Observation, ...], pages: tuple[PageResult, ...]
    ) -> tuple[tuple[Observation, ...], int, int]:
        values = {item.date: item.adjusted_close for item in existing}
        original = dict(values)
        latest_existing = existing[-1].date if existing else None
        for page in pages:
            seen: set[date] = set()
            for item in page.observations:
                if not page.start_date <= item.date <= page.end_date:
                    raise SourceError(
                        f"Yahoo observation {item.date} is outside its requested interval"
                    )
                if item.date in seen:
                    raise SourceError(f"Yahoo repeated observation date {item.date}")
                seen.add(item.date)
                prior = values.get(item.date)
                if prior is None:
                    values[item.date] = item.adjusted_close
                elif prior != item.adjusted_close:
                    if item.date != latest_existing:
                        raise SourceError(
                            f"Yahoo changed historical observation {item.date}; "
                            "only the latest stored date may be updated"
                        )
                    values[item.date] = item.adjusted_close
        added = sum(day not in original for day in values)
        updated = sum(original.get(day) != value for day, value in values.items() if day in original)
        merged = tuple(Observation(day, values[day]) for day in sorted(values))
        return merged, added, updated

    def run(
        self,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
        now: datetime | None = None,
    ) -> AcquisitionReport:
        report = AcquisitionReport()
        timestamp = now or datetime.now(timezone.utc)
        try:
            start = DEFAULT_START_DATE if start_date is None else parse_date_bound(start_date, "start date")
            end = date.today() if end_date is None else parse_date_bound(end_date, "end date")
            if start > end:
                raise SourceError("start date must not be after end date")
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise ValueError("acquisition timestamps must include a timezone")

            with self.store.lock():
                existing = self.store.load_locked()
                windows = self._windows(start, end, existing)
                pages: list[PageResult] = []
                for left, right in windows:
                    window_info = {"start": left.isoformat(), "end": right.isoformat()}
                    try:
                        page = self.client.fetch(left, right)
                        if page.start_date != left or page.end_date != right:
                            raise SourceError(
                                "Yahoo response provenance does not match its requested interval"
                            )
                    except Exception as exc:
                        report.requested_windows.append({**window_info, "error": str(exc)})
                        raise
                    pages.append(page)
                    report.requested_windows.append(
                        {**window_info, "source_url": page.source_url}
                    )
                if not pages:
                    report.status = "unchanged"
                    self._coverage(report, existing)
                    if self.store.active_path.exists():
                        report.sha256 = sha256(self.store.active_path.read_bytes())
                    return report

                merged, report.added, report.updated = self._merge(existing, tuple(pages))
                if not merged:
                    if existing:
                        report.status = "unchanged"
                        self._coverage(report, existing)
                        report.sha256 = sha256(self.store.active_path.read_bytes())
                    else:
                        report.status = "unchanged"
                    return report

                result = self.store.save_locked(merged, tuple(pages), timestamp)
                report.status = result["status"]
                report.sha256 = result["sha256"]
                self._coverage(report, merged)
        except Exception as exc:
            report.status = "failed"
            report.errors.append(str(exc))
        return report

    @staticmethod
    def _coverage(report: AcquisitionReport, observations: tuple[Observation, ...]) -> None:
        report.observations = len(observations)
        if observations:
            report.first_date = observations[0].date.isoformat()
            report.last_date = observations[-1].date.isoformat()
