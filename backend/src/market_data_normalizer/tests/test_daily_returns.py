import csv
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


class DailyReturnsTests(unittest.TestCase):
    def test_calculates_daily_returns_with_sparse_series_and_sp500_fx_gap_baseline(self):
        from backend.src.market_data_normalizer.daily_returns import generate_daily_returns_reais

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_gathered(data_dir, [
                ["2011-01-03", "100", "20", "0.04", "100"],
                ["2011-01-04", "110", "", "", "105"],
                ["2011-01-05", "", "22", "0.05", ""],
                ["2011-01-06", "121", "24.2", "", "110"],
            ])
            self._write_currency(data_dir, [
                ["03.01.2011", "2,0000"],
                ["04.01.2011", "2,2000"],
                ["05.01.2011", "2,4200"],
            ])

            output_path = generate_daily_returns_reais(data_dir)
            result = pd.read_csv(output_path)

        self.assertEqual(list(result.columns), ["date", "ibovespa", "ifix", "selic", "sp500"])
        self.assertEqual(result["date"].tolist(), ["2011-01-04", "2011-01-05", "2011-01-06"])
        self.assertAlmostEqual(result.loc[0, "ibovespa"], 0.1)
        self.assertAlmostEqual(result.loc[0, "ifix"], 0.0)
        self.assertAlmostEqual(result.loc[0, "selic"], 0.0)
        self.assertAlmostEqual(result.loc[0, "sp500"], 0.155)
        self.assertAlmostEqual(result.loc[1, "ibovespa"], 0.0)
        self.assertAlmostEqual(result.loc[1, "ifix"], 0.1)
        self.assertAlmostEqual(result.loc[1, "selic"], 0.0005)
        self.assertAlmostEqual(result.loc[1, "sp500"], 0.0)
        self.assertAlmostEqual(result.loc[2, "ibovespa"], 0.1)
        self.assertAlmostEqual(result.loc[2, "ifix"], 0.1)
        self.assertAlmostEqual(result.loc[2, "selic"], 0.0)
        self.assertAlmostEqual(result.loc[2, "sp500"], (110 / 105) * (2.42 / 2.2) - 1)

    def test_missing_history_and_currency_produce_zero_until_next_return_is_calculable(self):
        from backend.src.market_data_normalizer.daily_returns import generate_daily_returns_reais

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_gathered(data_dir, [
                ["2011-01-03", "", "", "", ""],
                ["2011-01-04", "100", "", "", "100"],
                ["2011-01-05", "110", "", "", "110"],
                ["2011-01-06", "121", "", "", "121"],
            ])
            self._write_currency(data_dir, [["05.01.2011", "2,0000"], ["06.01.2011", "2,2000"]])

            result = pd.read_csv(generate_daily_returns_reais(data_dir))

        self.assertEqual(result[["ibovespa", "ifix", "selic", "sp500"]].iloc[0].tolist(), [0, 0, 0, 0])
        self.assertAlmostEqual(result.loc[1, "ibovespa"], 0.1)
        self.assertEqual(result.loc[1, "sp500"], 0)
        self.assertAlmostEqual(result.loc[2, "ibovespa"], 0.1)
        self.assertAlmostEqual(result.loc[2, "sp500"], 0.21)

    def test_handles_user_example(self):
        from backend.src.market_data_normalizer.daily_returns import generate_daily_returns_reais

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_gathered(data_dir, [
                ["2011-01-03", "69962.32", "1001.11", "0.040239", "1271.87"],
                ["2011-01-04", "70317.79", "992.56", "0.040203", "1270.2"],
            ])
            self._write_currency(data_dir, [["03.01.2011", "1,6465"], ["04.01.2011", "1,6605"]])

            result = pd.read_csv(generate_daily_returns_reais(data_dir))

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result.loc[0, "ibovespa"], 0.00508087782108979)
        self.assertAlmostEqual(result.loc[0, "ifix"], -0.00854052002277483)
        self.assertAlmostEqual(result.loc[0, "selic"], 0.00040203)
        self.assertAlmostEqual(result.loc[0, "sp500"], 0.00717869311278152)

    def test_rejects_invalid_gathered_input_without_changing_existing_output(self):
        from backend.src.market_data_normalizer.daily_returns import NormalizationError, generate_daily_returns_reais

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_gathered(data_dir, [
                ["2011-01-03", "100", "20", "0.04", "100"],
                ["2011-01-02", "110", "21", "0.04", "110"],
            ])
            self._write_currency(data_dir, [["03.01.2011", "2,0000"]])
            output_path = data_dir / "normalized/daily_returns_reais.csv"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("previous output\n", encoding="utf-8")

            with self.assertRaisesRegex(NormalizationError, "ascending"):
                generate_daily_returns_reais(data_dir)

            self.assertEqual(output_path.read_text(encoding="utf-8"), "previous output\n")

    def test_rejects_duplicate_currency_dates_and_preserves_output(self):
        from backend.src.market_data_normalizer.daily_returns import NormalizationError, generate_daily_returns_reais

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_gathered(data_dir, [["2011-01-03", "100", "20", "0.04", "100"]])
            self._write_currency(data_dir, [["03.01.2011", "2,0000"], ["03.01.2011", "2,1000"]])
            output_path = data_dir / "normalized/daily_returns_reais.csv"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("previous output\n", encoding="utf-8")

            with self.assertRaisesRegex(NormalizationError, "duplicate currency dates"):
                generate_daily_returns_reais(data_dir)

            self.assertEqual(output_path.read_text(encoding="utf-8"), "previous output\n")

    def test_underwidth_gathered_row_raises_contextual_error_and_preserves_output(self):
        from backend.src.market_data_normalizer.daily_returns import NormalizationError, generate_daily_returns_reais

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            gathered_path = data_dir / "normalized/gathered_data.csv"
            gathered_path.parent.mkdir(parents=True, exist_ok=True)
            gathered_path.write_text(
                "date,ibovespa,ifix,selic,sp500\n"
                "2011-01-03,100,20,0.04,100\n"
                "2011-01-04,110,21,0.04\n",
                encoding="utf-8",
            )
            self._write_currency(data_dir, [["03.01.2011", "2,0000"]])
            output_path = data_dir / "normalized/daily_returns_reais.csv"
            output_path.write_text("previous output\n", encoding="utf-8")

            with self.assertRaises(NormalizationError) as raised:
                generate_daily_returns_reais(data_dir)

            message = str(raised.exception)
            self.assertIn("gathered_data.csv", message)
            self.assertIn("row 3", message)
            self.assertIn("sp500", message)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "previous output\n")

    def test_underwidth_currency_row_raises_contextual_error_and_preserves_output(self):
        from backend.src.market_data_normalizer.daily_returns import NormalizationError, generate_daily_returns_reais

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_gathered(data_dir, [
                ["2011-01-03", "100", "20", "0.04", "100"],
                ["2011-01-04", "110", "21", "0.04", "110"],
            ])
            currency_path = data_dir / "dolar/source/USD_BRL.csv"
            currency_path.parent.mkdir(parents=True, exist_ok=True)
            currency_path.write_text(
                "Data,price\n03.01.2011,\"2,0000\"\n04.01.2011\n",
                encoding="utf-8",
            )
            output_path = data_dir / "normalized/daily_returns_reais.csv"
            output_path.write_text("previous output\n", encoding="utf-8")

            with self.assertRaises(NormalizationError) as raised:
                generate_daily_returns_reais(data_dir)

            message = str(raised.exception)
            self.assertIn("USD_BRL.csv", message)
            self.assertIn("row 3", message)
            self.assertIn("price", message)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "previous output\n")

    def test_reads_multiple_currency_files_and_rejects_duplicate_dates_across_them(self):
        from backend.src.market_data_normalizer.daily_returns import NormalizationError, generate_daily_returns_reais

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_gathered(data_dir, [
                ["2011-01-03", "100", "20", "0.04", "100"],
                ["2011-01-04", "110", "21", "0.04", "110"],
            ])
            self._write_currency(data_dir, [["04.01.2011", "2,2000"]], filename="a.csv")
            self._write_currency(data_dir, [["03.01.2011", "2,0000"]], filename="b.csv")
            output_path = generate_daily_returns_reais(data_dir)
            result = pd.read_csv(output_path)
            self.assertAlmostEqual(result.loc[0, "sp500"], 0.21)

            self._write_currency(data_dir, [["03.01.2011", "2,1000"]], filename="c.csv")
            with self.assertRaisesRegex(NormalizationError, "duplicate currency dates"):
                generate_daily_returns_reais(data_dir)

    def test_rejects_nonfinite_and_nonpositive_index_levels(self):
        from backend.src.market_data_normalizer.daily_returns import NormalizationError, generate_daily_returns_reais

        for bad_value, error_text in (("1e999", "non-finite ibovespa"), ("0", "ibovespa must be positive")):
            with self.subTest(bad_value=bad_value), tempfile.TemporaryDirectory() as temporary_directory:
                data_dir = Path(temporary_directory)
                self._write_gathered(data_dir, [
                    ["2011-01-03", "100", "20", "0.04", "100"],
                    ["2011-01-04", bad_value, "21", "0.04", "110"],
                ])
                self._write_currency(data_dir, [["03.01.2011", "2,0000"]])

                with self.assertRaisesRegex(NormalizationError, error_text):
                    generate_daily_returns_reais(data_dir)

    def test_atomic_replace_failure_keeps_published_output_and_cleans_temporary_file(self):
        from backend.src.market_data_normalizer.daily_returns import NormalizationError, generate_daily_returns_reais

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_gathered(data_dir, [["2011-01-03", "100", "20", "0.04", "100"],
                                            ["2011-01-04", "110", "22", "0.04", "110"]])
            self._write_currency(data_dir, [["03.01.2011", "2,0000"], ["04.01.2011", "2,1000"]])
            output_path = data_dir / "normalized/daily_returns_reais.csv"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("previous output\n", encoding="utf-8")

            with patch("backend.src.market_data_normalizer.daily_returns.service.os.replace", side_effect=OSError("replace blocked")):
                with self.assertRaisesRegex(NormalizationError, "unable to publish"):
                    generate_daily_returns_reais(data_dir)

            self.assertEqual(output_path.read_text(encoding="utf-8"), "previous output\n")
            self.assertEqual(list(output_path.parent.glob(".daily_returns_reais.*.csv")), [])

    def test_default_root_is_independent_of_working_directory(self):
        from backend.src.market_data_normalizer.daily_returns import generate_daily_returns_reais
        import backend.src.market_data_normalizer.daily_returns.service as service

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_gathered(data_dir, [["2011-01-03", "100", "20", "0.04", "100"]])
            self._write_currency(data_dir, [["03.01.2011", "2,0000"]])
            with patch.object(service, "_REPOSITORY_DATA", data_dir):
                self.assertEqual(generate_daily_returns_reais(), data_dir / "normalized/daily_returns_reais.csv")

    def test_import_has_no_csv_side_effects(self):
        import backend.src.market_data_normalizer.daily_returns.service as service
        import backend.src.market_data_normalizer.daily_returns as public_api

        with patch("pandas.read_csv", side_effect=AssertionError("import read CSV")), patch(
            "pandas.DataFrame.to_csv", side_effect=AssertionError("import wrote CSV")
        ):
            importlib.reload(service)
        public_api.NormalizationError = service.NormalizationError
        public_api.generate_daily_returns_reais = service.generate_daily_returns_reais

    @staticmethod
    def _write_gathered(data_dir, rows):
        path = data_dir / "normalized/gathered_data.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "ibovespa", "ifix", "selic", "sp500"])
            writer.writerows(rows)

    @staticmethod
    def _write_currency(data_dir, rows, filename="USD_BRL.csv"):
        path = data_dir / "dolar/source" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Data", "price"])
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
