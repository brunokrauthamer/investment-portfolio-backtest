import unittest
from unittest.mock import patch

class GetterPublicTests(unittest.TestCase):
    def test_public_entry_point_is_available_without_network_on_import(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("unexpected network")):
            from backend.src.internet_data_getter import acquire_ifix
            self.assertTrue(callable(acquire_ifix))

    def test_public_entry_point_uses_requested_data_directory(self):
        from backend.src.internet_data_getter import acquire_ifix
        with patch("backend.src.internet_data_getter.ifix.B3IfixClient") as client, \
             patch("backend.src.internet_data_getter.ifix.FileStore") as store, \
             patch("backend.src.internet_data_getter.ifix.IfixAcquisition") as service:
            result = acquire_ifix("chosen-data")
            store.assert_called_once_with("chosen-data")
            service.assert_called_once_with(client.return_value, store.return_value)
            self.assertIs(result, service.return_value.run.return_value)


class GenericGetterTests(unittest.TestCase):
    def test_all_getters_run_and_return_keyed_results(self):
        from backend.src.internet_data_getter import acquire_all, _Getter
        from unittest.mock import Mock
        a, b = Mock(return_value="first"), Mock(return_value="second")
        with patch("backend.src.internet_data_getter._GETTERS", {"a": _Getter(a, None), "b": _Getter(b, None)}):
            self.assertEqual(acquire_all("dir"), {"a": "first", "b": "second"})
            a.assert_called_once_with("dir")
            b.assert_called_once_with("dir")

    def test_selecting_a_getter_runs_only_that_getter(self):
        from backend.src.internet_data_getter import acquire, _Getter
        from unittest.mock import Mock
        a, b = Mock(return_value="first"), Mock(return_value="second")
        with patch("backend.src.internet_data_getter._GETTERS", {"a": _Getter(a, None), "b": _Getter(b, None)}):
            self.assertEqual(acquire("b", "dir"), "second")
            a.assert_not_called()
            b.assert_called_once_with("dir")
            with self.assertRaises(ValueError):
                acquire("missing", "dir")

    def test_cli_runs_all_or_only_selected_getter(self):
        from backend.src.internet_data_getter import _Getter, __main__ as cli
        from unittest.mock import Mock
        a, b = Mock(return_value=Mock(complete=True)), Mock(return_value=Mock(complete=True))
        handlers = {"a": _Getter(a, Mock()), "b": _Getter(b, Mock())}
        with patch("backend.src.internet_data_getter._GETTERS", handlers), \
             patch.object(cli, "_GETTERS", handlers):
            self.assertEqual(cli.main([]), 0)
            a.assert_called_once()
            b.assert_called_once()
            a.reset_mock()
            b.reset_mock()
            self.assertEqual(cli.main(["--getter", "b"]), 0)
            a.assert_not_called()
            b.assert_called_once()

    def test_cli_continues_after_one_getter_fails(self):
        from backend.src.internet_data_getter import _Getter, __main__ as cli
        from unittest.mock import Mock
        a = Mock(side_effect=OSError("offline"))
        b = Mock(return_value=Mock(complete=True))
        handlers = {"a": _Getter(a, Mock()), "b": _Getter(b, Mock())}
        with patch("backend.src.internet_data_getter._GETTERS", handlers), \
             patch.object(cli, "_GETTERS", handlers):
            self.assertEqual(cli.main([]), 1)
            b.assert_called_once()
