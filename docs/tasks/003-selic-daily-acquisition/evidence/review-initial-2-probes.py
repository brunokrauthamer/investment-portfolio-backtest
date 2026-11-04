"""Independent round 2 probes. All observations here are controlled fixtures."""
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from backend.src.internet_data_getter.selic import storage
from backend.src.internet_data_getter.selic.source import (
    Observation, SourceError, SourceResult, parse_observation_rows, validate_observations,
)


def result(rate):
    day = date(2011, 2, 2)
    return SourceResult((Observation(day, rate),), day, 1)


def stamp(day):
    return datetime(2026, 2, day, tzinfo=timezone.utc)


with TemporaryDirectory() as temporary:
    store = storage.SelicFileStore(Path(temporary))
    store.save(result('9.991'), stamp(1))
    atomic_write = storage._atomic_write

    def interrupt(path, content):
        if path == store.manifest_path:
            raise OSError('simulated interruption after active CSV replacement')
        return atomic_write(path, content)

    try:
        with patch.object(storage, '_atomic_write', side_effect=interrupt):
            store.save(result('9.992'), stamp(2))
    except OSError:
        pass
    pending = store.pending_path.read_bytes()
    unrelated = b'{"unrecognized": "preserve this live manifest"}\n'
    store.manifest_path.write_bytes(unrelated)
    try:
        with store.lock():
            store.recover()
    except storage.ManifestError:
        pass
    assert store.manifest_path.read_bytes() == unrelated
    assert store.pending_path.read_bytes() == pending
    print('UNKNOWN_MANIFEST_AND_PENDING_PRESERVED True')

with TemporaryDirectory() as temporary:
    store = storage.SelicFileStore(Path(temporary))
    sizes = []
    for day in range(1, 11):
        store.save(result(f'9.99{day}'), stamp(day))
        sizes.append(store.manifest_path.stat().st_size)
    manifest = json.loads(store.manifest_path.read_bytes())
    print('MANIFEST_SIZE_BY_VERSION', sizes)
    assert all('record' not in r for r in manifest['current']['previous_versions'])
    old = manifest['current']['previous_versions'][0]
    store.restore(old['csv_path'], stamp(11))
    restored = json.loads(store.manifest_path.read_bytes())['current']
    assert restored['retrieved_at'] == '2026-02-01T00:00:00Z'
    assert restored['restored_at'] == '2026-02-11T00:00:00Z'
    print('RESTORE_PROVENANCE_PRESERVED True')

with TemporaryDirectory() as temporary:
    store = storage.SelicFileStore(Path(temporary))
    store.save(result('9.991'), stamp(1))
    manifest = json.loads(store.manifest_path.read_bytes())
    manifest['current']['retrieved_at'] = None
    manifest['current']['observation_count'] = 99
    manifest.pop('unit')
    store.manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    try:
        status = store.save(result('9.991'), stamp(2))['status']
    except storage.ManifestError:
        status = 'rejected'
    print('CORRUPT_PROVENANCE_RERUN_STATUS', status)

rows = (
    ('Date DD/MM/YYYY', '11 % p.d.'),
    ('02/02/2011', '9,991'),
    ('03-02-2011', '9,992'),
    ('04/02/2011', '9,993'),
    ('Source', 'BCB-Demab'),
)
try:
    parsed = parse_observation_rows(rows)
    status = f'accepted {len(validate_observations(parsed, date(2011, 2, 4), 2))} rows'
except SourceError:
    status = 'rejected'
print('MALFORMED_DATE_ROW_STATUS', status)
