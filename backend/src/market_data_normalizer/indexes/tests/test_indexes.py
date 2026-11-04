import tempfile
import unittest
from pathlib import Path
import importlib
from unittest.mock import patch

import pandas as pd


class IndexGatheringTests(unittest.TestCase):
    def test_gathers_values_from_each_source_into_one_ordered_table(self):
        try:
            from backend.src.market_data_normalizer.indexes import gather_index_data
        except ImportError:
            gather_index_data = None
        self.assertIsNotNone(gather_index_data, "public gather_index_data function is unavailable")

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_b3(data_dir / "ibovespa/source/ibovespa.csv", "IBOV", 2011, {("Jan", 3): "187.952,91"})
            self._write_b3(data_dir / "ifix/source/ifix.csv", "IFIX", 2011, {("Jan", 4): "3.778,89"})
            self._write_b3(data_dir / "ifix/source/ifix_2012.csv", "IFIX", 2012, {("Fev", 29): "2.999,01"})
            self._write_table(data_dir / "selic/source/selic.csv", ["date", "rate_percent_per_day"], [["2011-01-03", "0.040239"]])
            self._write_table(data_dir / "sp500/source/sp500.csv", ["date", "adjusted_close"], [["2011-01-05", "1271.870000"]])
            sources = [
                (data_dir / "ibovespa/source/ibovespa.csv", {"sep": ";", "encoding": "cp1252", "engine": "python", "header": None, "names": list(range(13))}),
                (data_dir / "ifix/source/ifix.csv", {"sep": ";", "encoding": "cp1252", "engine": "python", "header": None, "names": list(range(13))}),
                (data_dir / "ifix/source/ifix_2012.csv", {"sep": ";", "encoding": "cp1252", "engine": "python", "header": None, "names": list(range(13))}),
                (data_dir / "selic/source/selic.csv", {}),
                (data_dir / "sp500/source/sp500.csv", {}),
            ]
            before = [pd.read_csv(path, dtype=str, keep_default_na=False, **options) for path, options in sources]

            output_path = gather_index_data(data_dir)
            output = pd.read_csv(output_path, dtype=str, keep_default_na=False)
            after = [pd.read_csv(path, dtype=str, keep_default_na=False, **options) for path, options in sources]

        self.assertEqual(list(output.columns), ["date", "ibovespa", "ifix", "selic", "sp500"])
        self.assertEqual(output.to_dict(orient="records"), [
            {"date": "2011-01-03", "ibovespa": "187952.91", "ifix": "", "selic": "0.040239", "sp500": ""},
            {"date": "2011-01-04", "ibovespa": "", "ifix": "3778.89", "selic": "", "sp500": ""},
            {"date": "2011-01-05", "ibovespa": "", "ifix": "", "selic": "", "sp500": "1271.870000"},
            {"date": "2012-02-29", "ibovespa": "", "ifix": "2999.01", "selic": "", "sp500": ""},
        ])
        for previous, current in zip(before, after):
            pd.testing.assert_frame_equal(current, previous)

    def test_reads_each_direct_csv_and_rejects_duplicate_asset_dates(self):
        try:
            from backend.src.market_data_normalizer.indexes import gather_index_data, NormalizationError
        except ImportError:
            self.fail("public index normalizer API is unavailable")

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_b3(data_dir / "ibovespa/source/ibovespa.csv", "IBOV", 2011, {("Jan", 3): "187.952,91"})
            self._write_b3(data_dir / "ifix/source/ifix.csv", "IFIX", 2011, {("Jan", 3): "3.778,89"})
            self._write_table(data_dir / "selic/source/a.csv", ["date", "rate_percent_per_day"], [["2011-01-03", "0.040239"]])
            self._write_table(data_dir / "selic/source/b.csv", ["date", "rate_percent_per_day"], [["2011-01-04", "0.040203"]])
            self._write_table(data_dir / "sp500/source/sp500.csv", ["date", "adjusted_close"], [["2011-01-05", "1271.87"]])
            self._write_table(data_dir / "sp500/source/nested/ignored.csv", ["date", "adjusted_close"], [["2011-01-06", "9999.99"]])

            output_path = gather_index_data(data_dir)
            output = pd.read_csv(output_path, dtype=str, keep_default_na=False)
            self.assertEqual(list(output["date"]), ["2011-01-03", "2011-01-04", "2011-01-05"])
            self._write_table(data_dir / "sp500/source/duplicate.csv", ["date", "adjusted_close"], [["2011-01-05", "1272.00"]])

            with self.assertRaisesRegex(NormalizationError, "duplicate sp500 dates"):
                gather_index_data(data_dir)

    def test_rejects_populated_impossible_b3_date_and_preserves_published_file(self):
        try:
            from backend.src.market_data_normalizer.indexes import gather_index_data, NormalizationError
        except ImportError:
            self.fail("public index normalizer API is unavailable")

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_b3(data_dir / "ibovespa/source/ibovespa.csv", "IBOV", 2011, {("Jan", 3): "187.952,91"})
            self._write_b3(data_dir / "ifix/source/ifix.csv", "IFIX", 2011, {("Jan", 3): "3.778,89"})
            self._write_table(data_dir / "selic/source/selic.csv", ["date", "rate_percent_per_day"], [["2011-01-03", "0.040239"]])
            self._write_table(data_dir / "sp500/source/sp500.csv", ["date", "adjusted_close"], [["2011-01-03", "1271.87"]])
            output_path = gather_index_data(data_dir)
            previous = pd.read_csv(output_path, dtype=str, keep_default_na=False)

            self._write_b3(data_dir / "ifix/source/ifix.csv", "IFIX", 2011, {("Fev", 31): "3.778,89"})
            with self.assertRaisesRegex(NormalizationError, "invalid date 2011-02-31"):
                gather_index_data(data_dir)

            self._write_b3(data_dir / "ifix/source/ifix.csv", "IFIX", 2011, {("Jan", 3): "not-a-number"})
            with self.assertRaisesRegex(NormalizationError, "invalid IFIX"):
                gather_index_data(data_dir)

            current = pd.read_csv(output_path, dtype=str, keep_default_na=False)
        pd.testing.assert_frame_equal(current, previous)

    def test_rejects_malformed_daily_value_and_invalid_schema(self):
        try:
            from backend.src.market_data_normalizer.indexes import gather_index_data, NormalizationError
        except ImportError:
            self.fail("public index normalizer API is unavailable")

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_b3(data_dir / "ibovespa/source/ibovespa.csv", "IBOV", 2011, {("Jan", 3): "187.952,91"})
            self._write_b3(data_dir / "ifix/source/ifix.csv", "IFIX", 2011, {("Jan", 3): "3.778,89"})
            self._write_table(data_dir / "selic/source/selic.csv", ["date", "rate_percent_per_day"], [["2011-01-03", "invalid"]])
            self._write_table(data_dir / "sp500/source/sp500.csv", ["date", "adjusted_close"], [["2011-01-03", "1271.87"]])
            with self.assertRaisesRegex(NormalizationError, "invalid rate_percent_per_day"):
                gather_index_data(data_dir)

            self._write_table(data_dir / "selic/source/selic.csv", ["day", "rate"], [["2011-01-03", "0.040239"]])
            with self.assertRaisesRegex(NormalizationError, "expected columns"):
                gather_index_data(data_dir)

            self._write_table(data_dir / "selic/source/selic.csv", ["date", "rate_percent_per_day"], [["2011-02-30", "0.040239"]])
            with self.assertRaisesRegex(NormalizationError, "invalid date"):
                gather_index_data(data_dir)

    def test_missing_source_files_fail_before_creating_output(self):
        try:
            from backend.src.market_data_normalizer.indexes import gather_index_data, NormalizationError
        except ImportError:
            self.fail("public index normalizer API is unavailable")

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            (data_dir / "ibovespa/source").mkdir(parents=True)
            with self.assertRaisesRegex(NormalizationError, "no CSV source files for ibovespa"):
                gather_index_data(data_dir)
            self.assertFalse((data_dir / "normalized/gathered_data.csv").exists())

    def test_atomic_replace_failure_keeps_previous_output_and_cleans_temporary_file(self):
        try:
            from backend.src.market_data_normalizer.indexes import gather_index_data, NormalizationError
        except ImportError:
            self.fail("public index normalizer API is unavailable")

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_b3(data_dir / "ibovespa/source/ibovespa.csv", "IBOV", 2011, {("Jan", 3): "187.952,91"})
            self._write_b3(data_dir / "ifix/source/ifix.csv", "IFIX", 2011, {("Jan", 3): "3.778,89"})
            self._write_table(data_dir / "selic/source/selic.csv", ["date", "rate_percent_per_day"], [["2011-01-03", "0.040239"]])
            self._write_table(data_dir / "sp500/source/sp500.csv", ["date", "adjusted_close"], [["2011-01-03", "1271.87"]])
            output_path = gather_index_data(data_dir)
            previous = pd.read_csv(output_path, dtype=str, keep_default_na=False)
            with patch("backend.src.market_data_normalizer.indexes.service.os.replace", side_effect=OSError("replace blocked")):
                with self.assertRaisesRegex(NormalizationError, "unable to publish"):
                    gather_index_data(data_dir)

            current = pd.read_csv(output_path, dtype=str, keep_default_na=False)
            temporary_files = list(output_path.parent.glob(".gathered_data.*.csv"))
        pd.testing.assert_frame_equal(current, previous)
        self.assertEqual(temporary_files, [])

    def test_import_does_not_read_or_write_csv_files(self):
        import backend.src.market_data_normalizer.indexes.service as service

        with patch("pandas.read_csv", side_effect=AssertionError("import read a CSV")), patch(
            "pandas.DataFrame.to_csv", side_effect=AssertionError("import wrote a CSV")
        ):
            importlib.reload(service)

    def test_short_b3_row_fails_with_source_context(self):
        from backend.src.market_data_normalizer.indexes import gather_index_data, NormalizationError

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_complete_sources(data_dir)
            malformed_path = data_dir / "ibovespa/source/ibovespa.csv"
            self._write_b3(
                malformed_path,
                "IBOV",
                2011,
                {("Jan", 1): "70.000,00"},
                short_day=2,
            )

            with self.assertRaisesRegex(NormalizationError, r"ibovespa\.csv.*row 4.*13 fields"):
                gather_index_data(data_dir)

    def test_overwide_daily_row_fails_with_source_context(self):
        from backend.src.market_data_normalizer.indexes import gather_index_data, NormalizationError

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_complete_sources(data_dir)
            malformed_path = data_dir / "selic/source/selic.csv"
            self._write_overwide_table(
                malformed_path,
                ["date", "rate_percent_per_day"],
                ["unexpected", "2024-01-02", "1.000"],
            )

            with self.assertRaisesRegex(NormalizationError, r"selic\.csv.*row width.*two columns"):
                gather_index_data(data_dir)

    def test_csv_suffixed_directory_is_skipped(self):
        from backend.src.market_data_normalizer.indexes import gather_index_data

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_complete_sources(data_dir)
            (data_dir / "sp500/source/a-directory.csv").mkdir()

            output_path = gather_index_data(data_dir)
            output = pd.read_csv(output_path, dtype=str, keep_default_na=False)
            self.assertEqual(list(output["date"]), ["2011-01-03"])

    def test_numeric_footer_label_is_rejected_instead_of_hiding_observation(self):
        from backend.src.market_data_normalizer.indexes import gather_index_data, NormalizationError

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_complete_sources(data_dir)
            self._write_b3(
                data_dir / "ibovespa/source/ibovespa.csv",
                "IBOV",
                2024,
                {("Jan", 2): "1.234,00"},
                footer_rows=[["2", "9.999,00"] + [""] * 11, ["MÁXIMO"] + [""] * 12],
            )

            with self.assertRaisesRegex(NormalizationError, r"ibovespa\.csv.*summary row.*nonnumeric label"):
                gather_index_data(data_dir)

    def test_nul_and_trailing_text_in_daily_value_is_rejected(self):
        from backend.src.market_data_normalizer.indexes import gather_index_data, NormalizationError

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_complete_sources(data_dir)
            self._write_table(
                data_dir / "selic/source/selic.csv",
                ["date", "rate_percent_per_day"],
                [["2024-01-02", "0.040239\x00corrupted"]],
            )

            with self.assertRaisesRegex(NormalizationError, r"selic\.csv.*malformed CSV.*NULL byte"):
                gather_index_data(data_dir)

    @classmethod
    def _write_complete_sources(cls, data_dir):
        cls._write_b3(data_dir / "ibovespa/source/ibovespa.csv", "IBOV", 2011, {("Jan", 3): "187.952,91"})
        cls._write_b3(data_dir / "ifix/source/ifix.csv", "IFIX", 2011, {("Jan", 3): "3.778,89"})
        cls._write_table(data_dir / "selic/source/selic.csv", ["date", "rate_percent_per_day"], [["2011-01-03", "0.040239"]])
        cls._write_table(data_dir / "sp500/source/sp500.csv", ["date", "adjusted_close"], [["2011-01-03", "1271.87"]])

    @staticmethod
    def _write_overwide_table(path, columns, row):
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([columns]).to_csv(path, index=False, header=False)
        pd.DataFrame([row]).to_csv(path, index=False, header=False, mode="a")

    @staticmethod
    def _write_b3(path, index_name, year, observations, short_day=None, footer_rows=None):
        path.parent.mkdir(parents=True, exist_ok=True)
        months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        rows = [[f"{index_name} - {year}"], ["Dia"] + months]
        for day in range(1, 32):
            row = [str(day)] + [observations.get((month, day), "") for month in months]
            rows.append(row[:2] if day == short_day else row)
        rows.extend(footer_rows or [["MÍNIMO"] + [""] * 12, ["MÁXIMO"] + [""] * 12])
        pd.DataFrame(rows[:1]).to_csv(path, sep=";", header=False, index=False, encoding="cp1252")
        if short_day is None:
            pd.DataFrame(rows[1:]).to_csv(path, sep=";", header=False, index=False, encoding="cp1252", mode="a")
        else:
            for row in rows[1:]:
                pd.DataFrame([row]).to_csv(path, sep=";", header=False, index=False, encoding="cp1252", mode="a")

    @staticmethod
    def _write_table(path, columns, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows, columns=columns).to_csv(path, index=False)


if __name__ == "__main__":
    unittest.main()
