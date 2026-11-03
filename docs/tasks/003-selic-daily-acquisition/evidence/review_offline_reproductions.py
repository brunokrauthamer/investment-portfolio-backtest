"""Review probes using only disposable storage and controlled values."""
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from backend.src.internet_data_getter.selic import storage
from backend.src.internet_data_getter.selic.source import Observation, SourceResult, _verify_values_page


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
    assert store.pending_path.exists()
    unrelated = b'{"unrecognized": "preserve this live manifest"}\n'
    store.manifest_path.write_bytes(unrelated)
    try:
        with store.lock():
            store.recover()
    except storage.ManifestError:
        pass
    print('UNKNOWN_MANIFEST_PRESERVED', store.manifest_path.read_bytes() == unrelated)
    print('RECOVERY_RECORD_PRESERVED', store.pending_path.exists())

with TemporaryDirectory() as temporary:
    store = storage.SelicFileStore(Path(temporary))
    sizes = []
    for day in range(1, 11):
        store.save(result(f'9.99{day}'), stamp(day))
        sizes.append(store.manifest_path.stat().st_size)
    manifest = json.loads(store.manifest_path.read_bytes())
    print('MANIFEST_SIZE_BY_VERSION', sizes)
    old = manifest['current']['previous_versions'][0]
    store.restore(old['csv_path'], stamp(11))
    restored = json.loads(store.manifest_path.read_bytes())['current']
    print('ORIGINAL_RETRIEVAL', old['record']['retrieved_at'])
    print('RESTORED_RETRIEVAL', restored['retrieved_at'])


class Locator:
    def __init__(self, text):
        self.text = text

    def inner_text(self):
        return self.text

    def all(self):
        return []


class Page:
    def locator(self, selector):
        return Locator({
            '#seriesSelecionadas': '111 - Interest rate - Selic\nPeriod 01/01/2011 to 11/02/2011\nLinear',
            '#valoresSeries': 'Found registers by series: 1\nDate\n111 % p.d.',
        }.get(selector, ''))


try:
    _verify_values_page(Page(), '11/02/2011')
except Exception:
    print('WRONG_SERIES_REJECTED', True)
else:
    print('WRONG_SERIES_REJECTED', False)
