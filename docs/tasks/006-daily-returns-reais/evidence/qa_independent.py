"""Independent offline checks for daily returns AC-001 through AC-007."""

from __future__ import annotations

import csv
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from backend.src.market_data_normalizer.daily_returns import (
    NormalizationError,
    generate_daily_returns_reais,
)


DATA = ROOT / "data"
GATHERED = DATA / "normalized" / "gathered_data.csv"
CURRENCY = DATA / "dolar" / "source" / "USD_BRL Dados Históricos (1).csv"
OUTPUT = DATA / "normalized" / "daily_returns_reais.csv"
COLUMNS = ["date", "ibovespa", "ifix", "selic", "sp500"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decimal(text: str) -> Decimal | None:
    return Decimal(text) if text.strip() else None


def close(actual: str, expected: Decimal) -> bool:
    return abs(Decimal(actual) - expected) < Decimal("1e-14")


def check_project_artifact() -> dict[str, object]:
    with GATHERED.open(encoding="utf-8", newline="") as handle:
        gathered = list(csv.DictReader(handle))
    with CURRENCY.open(encoding="utf-8-sig", newline="") as handle:
        currency_rows = list(csv.DictReader(handle))
    currency: dict[str, Decimal] = {}
    for row in currency_rows:
        day, month, year = row["Data"].split(".")
        currency[f"{year}-{month}-{day}"] = Decimal(row["price"].replace(",", "."))

    expected_rows = []
    last_values: dict[str, Decimal | None] = {key: None for key in COLUMNS[1:]}
    last_sp_fx: Decimal | None = None
    previous_sp: Decimal | None = None
    current_fx: Decimal | None = None
    sorted_fx = sorted(currency.items())
    cursor = 0
    for index, row in enumerate(gathered):
        while cursor < len(sorted_fx) and sorted_fx[cursor][0] <= row["date"]:
            current_fx = sorted_fx[cursor][1]
            cursor += 1
        calculated: dict[str, Decimal | str] = {"date": row["date"]}
        for asset in ("ibovespa", "ifix"):
            level = decimal(row[asset])
            calculated[asset] = (
                level / last_values[asset] - Decimal(1)
                if level is not None and last_values[asset] is not None
                else Decimal(0)
            )
            if level is not None:
                last_values[asset] = level
        selic = decimal(row["selic"])
        calculated["selic"] = selic / Decimal(100) if selic is not None else Decimal(0)
        sp = decimal(row["sp500"])
        sp_return = Decimal(0)
        if sp is not None:
            if previous_sp is not None and last_sp_fx is not None and current_fx is not None:
                sp_return = (current_fx / last_sp_fx) * (sp / previous_sp) - Decimal(1)
            previous_sp = sp
            last_sp_fx = current_fx
        calculated["sp500"] = sp_return
        if index:
            expected_rows.append(calculated)

    with OUTPUT.open(encoding="utf-8", newline="") as handle:
        actual_rows = list(csv.DictReader(handle))
    assert len(actual_rows) == len(expected_rows)
    assert list(actual_rows[0]) == COLUMNS
    assert [row["date"] for row in actual_rows] == [row["date"] for row in expected_rows]
    maximum_error = Decimal(0)
    checked_values = 0
    for actual, expected in zip(actual_rows, expected_rows):
        for asset in COLUMNS[1:]:
            difference = abs(Decimal(actual[asset]) - expected[asset])
            maximum_error = max(maximum_error, difference)
            assert difference < Decimal("1e-14"), (actual["date"], asset, difference)
            checked_values += 1
    example = next(row for row in actual_rows if row["date"] == "2011-01-04")
    assert abs(
        Decimal(example["ibovespa"]) - (Decimal("70317.79") / Decimal("69962.32") - 1)
    ) < Decimal("1e-14")
    assert abs(Decimal(example["sp500"]) - Decimal("0.00717869311278152")) < Decimal("1e-15")
    gap_row = next(row for row in actual_rows if row["date"] == "2011-01-17")
    assert Decimal(gap_row["sp500"]) == 0
    resume_row = next(row for row in actual_rows if row["date"] == "2011-01-18")
    assert Decimal(resume_row["sp500"]) != 0
    return {
        "rows": len(actual_rows),
        "columns": COLUMNS,
        "checked_return_values": checked_values,
        "maximum_absolute_decimal_error": str(maximum_error),
        "example_2011_01_04": example,
        "index_gap_2011_03_07_to_09": {
            row["date"]: {asset: row[asset] for asset in ("ibovespa", "ifix")}
            for row in actual_rows
            if row["date"] in {"2011-03-07", "2011-03-08", "2011-03-09"}
        },
        "s_and_p_gap_2011_01_17": gap_row["sp500"],
        "s_and_p_resumption_2011_01_18": resume_row["sp500"],
        "s_and_p_same_day_fx_missing_2026_11_04": next(
            row["sp500"] for row in actual_rows if row["date"] == "2026-11-04"
        ),
        "output_sha256": digest(OUTPUT),
    }


def write_fixtures(root: Path, gathered_text: str, currency_text: str = "Data,price\n03.01.2020,2.0\n") -> None:
    (root / "normalized").mkdir(parents=True, exist_ok=True)
    (root / "dolar" / "source").mkdir(parents=True, exist_ok=True)
    (root / "normalized" / "gathered_data.csv").write_text(gathered_text, encoding="utf-8")
    (root / "dolar" / "source" / "currency.csv").write_text(currency_text, encoding="utf-8")


def check_isolated_fixtures() -> dict[str, object]:
    full_rows = (
        "date,ibovespa,ifix,selic,sp500\n"
        "2020-01-03,100,200,4,1000\n"
        "2020-01-04,110,,5,1100\n"
        "2020-01-05,,220,,\n"
        "2020-01-06,121,242,2,1210\n"
        "2020-01-07,130,,3,1300\n"
    )
    fx_rows = "Data,price\n03.01.2020,2.0\n04.01.2020,2.2\n05.01.2020,2.42\n07.01.2020,2.662\n"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        write_fixtures(root, full_rows, fx_rows)
        output = generate_daily_returns_reais(root)
        with output.open(encoding="utf-8", newline="") as handle:
            values = list(csv.DictReader(handle))
        assert [row["date"] for row in values] == [
            "2020-01-04", "2020-01-05", "2020-01-06", "2020-01-07"
        ]
        assert close(values[0]["ibovespa"], Decimal("0.1"))
        assert Decimal(values[0]["ifix"]) == 0
        assert close(values[0]["selic"], Decimal("0.05"))
        assert close(values[0]["sp500"], Decimal("0.21"))
        assert Decimal(values[1]["sp500"]) == 0
        assert close(values[2]["ibovespa"], Decimal("0.1"))
        assert close(values[2]["ifix"], Decimal("0.1"))
        assert close(values[2]["sp500"], Decimal("0.21"))
        assert close(
            values[3]["sp500"],
            Decimal("1300") / Decimal("1210") * Decimal("2.662") / Decimal("2.42") - 1,
        )

        no_history = (
            "date,ibovespa,ifix,selic,sp500\n"
            "2020-01-03,,,4,1000\n"
            "2020-01-04,10,20,5,1100\n"
            "2020-01-05,11,22,6,1210\n"
        )
        write_fixtures(root, no_history, "Data,price\n04.01.2020,2.0\n05.01.2020,2.2\n")
        values = list(csv.DictReader(generate_daily_returns_reais(root).open(encoding="utf-8", newline="")))
        assert Decimal(values[0]["ibovespa"]) == 0
        assert Decimal(values[0]["sp500"]) == 0
        assert close(values[1]["ibovespa"], Decimal("0.1"))
        assert close(values[1]["sp500"], Decimal("0.21"))

        sentinel = b"old output\n"
        (root / "normalized" / "daily_returns_reais.csv").write_bytes(sentinel)
        short_gathered = full_rows + "2020-01-08,1,2,3\n"
        write_fixtures(root, short_gathered, fx_rows)
        try:
            generate_daily_returns_reais(root)
        except NormalizationError as error:
            assert "row 7" in str(error) and "sp500" in str(error)
        else:
            raise AssertionError("short gathered row was accepted")
        assert (root / "normalized" / "daily_returns_reais.csv").read_bytes() == sentinel

        write_fixtures(root, full_rows, fx_rows + "06.01.2020\n")
        try:
            generate_daily_returns_reais(root)
        except NormalizationError as error:
            assert "currency.csv" in str(error) and "price" in str(error)
        else:
            raise AssertionError("short currency row was accepted")
        assert (root / "normalized" / "daily_returns_reais.csv").read_bytes() == sentinel

        blank_gathered = (
            "date,ibovespa,ifix,selic,sp500\n"
            "2020-01-03,100,200,4,1000\n"
            "2020-01-04,110,,5,1100\n"
        )
        write_fixtures(root, blank_gathered, fx_rows)
        blank_values = list(csv.DictReader(generate_daily_returns_reais(root).open(encoding="utf-8", newline="")))
        assert Decimal(blank_values[0]["ifix"]) == 0
    return {
        "sparse_gaps_fx_bridge_missing_current_fx_first_history_short_rows_sentinel": "passed",
        "result_rows": 4,
    }


def check_rejected_inputs_preserve_output() -> dict[str, object]:
    valid_gathered = (
        "date,ibovespa,ifix,selic,sp500\n"
        "2020-01-03,100,200,4,1000\n"
        "2020-01-04,110,220,5,1100\n"
    )
    valid_currency = "Data,price\n03.01.2020,2.0\n04.01.2020,2.2\n"
    failures = {
        "invalid gathered date": (valid_gathered.replace("2020-01-04", "2020-02-30"), valid_currency),
        "duplicate gathered date": (valid_gathered + "2020-01-04,120,230,6,1200\n", valid_currency),
        "invalid currency date": (valid_gathered, "Data,price\n31.02.2020,2.0\n"),
        "duplicate currency date": (valid_gathered, valid_currency + "04.01.2020,2.3\n"),
        "incompatible gathered header": (valid_gathered.replace("ifix", "ifx", 1), valid_currency),
        "incompatible currency header": (valid_gathered, "Date,price\n03.01.2020,2.0\n"),
    }
    sentinel = b"sentinel output\n"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for label, (gathered_text, currency_text) in failures.items():
            write_fixtures(root, gathered_text, currency_text)
            output = root / "normalized" / "daily_returns_reais.csv"
            output.write_bytes(sentinel)
            try:
                generate_daily_returns_reais(root)
            except NormalizationError:
                pass
            else:
                raise AssertionError(f"{label} was accepted")
            assert output.read_bytes() == sentinel, label

        write_fixtures(root, valid_gathered, valid_currency)
        currency_file = root / "dolar" / "source" / "currency.csv"
        currency_file.unlink()
        output = root / "normalized" / "daily_returns_reais.csv"
        output.write_bytes(sentinel)
        try:
            generate_daily_returns_reais(root)
        except NormalizationError:
            pass
        else:
            raise AssertionError("missing currency input was accepted")
        assert output.read_bytes() == sentinel

        gathered_file = root / "normalized" / "gathered_data.csv"
        gathered_file.unlink()
        try:
            generate_daily_returns_reais(root)
        except NormalizationError:
            pass
        else:
            raise AssertionError("missing gathered input was accepted")
        assert output.read_bytes() == sentinel
    return {"rejected_cases": list(failures) + ["missing currency input", "missing gathered input"], "output_preserved": True}


def check_default_root_import_and_network_boundary() -> dict[str, object]:
    before_hashes = {str(path): digest(path) for path in (GATHERED, CURRENCY, OUTPUT)}
    code = f"""
import hashlib, pathlib, socket
root = pathlib.Path({str(ROOT)!r})
paths = [root / 'data/normalized/gathered_data.csv', root / 'data/dolar/source/USD_BRL Dados Históricos (1).csv', root / 'data/normalized/daily_returns_reais.csv']
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
before = [sha(path) for path in paths]
def denied(*args, **kwargs): raise AssertionError('network access attempted')
socket.socket.connect = denied
ns = {{}}
exec('from backend.src.market_data_normalizer.daily_returns import generate_daily_returns_reais', ns)
assert [sha(path) for path in paths] == before, 'import changed data files'
output = ns['generate_daily_returns_reais']()
assert output == root / 'data/normalized/daily_returns_reais.csv'
assert [sha(path) for path in paths] == before, 'execution changed source or output bytes'
print(str(output))
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT)
    with tempfile.TemporaryDirectory() as cwd:
        completed = subprocess.run(
            [str(ROOT / "backend/.venv/Scripts/python.exe"), "-c", code],
            cwd=cwd,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
    after_hashes = {str(path): digest(path) for path in (GATHERED, CURRENCY, OUTPUT)}
    assert before_hashes == after_hashes
    assert completed.stdout.strip() == str(OUTPUT)
    return {
        "default_root_works_from_temporary_cwd": True,
        "import_is_application_data_side_effect_free": True,
        "network_connect_blocked_and_not_used": True,
        "source_and_output_hashes_unchanged": True,
        "subprocess_stdout": completed.stdout.strip(),
    }


def main() -> None:
    gathered_hash_before = digest(GATHERED)
    currency_hash_before = digest(CURRENCY)
    project_artifact = check_project_artifact()
    isolated = check_isolated_fixtures()
    rejected = check_rejected_inputs_preserve_output()
    default_boundary = check_default_root_import_and_network_boundary()
    assert digest(GATHERED) == gathered_hash_before
    assert digest(CURRENCY) == currency_hash_before
    output = generate_daily_returns_reais()
    assert digest(OUTPUT) == project_artifact["output_sha256"]
    print({
        "project_artifact": project_artifact,
        "isolated": isolated,
        "invalid_and_missing_inputs": rejected,
        "default_root_and_import": default_boundary,
        "gathered_sha256_unchanged": gathered_hash_before,
        "currency_sha256_unchanged": currency_hash_before,
        "output_regeneration_matches": str(output) == str(OUTPUT),
    })


if __name__ == "__main__":
    main()
