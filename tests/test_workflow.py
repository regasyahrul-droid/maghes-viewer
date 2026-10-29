import base64
import hashlib
import unittest
from unittest.mock import MagicMock

from viewer_auth import authenticate
from viewer_submissions import (
    ASSET_TYPES,
    table_month,
    assigned_schemas,
    build_table_name,
    submit_request,
    submit_requests,
)


class WorkflowTests(unittest.TestCase):
    @staticmethod
    def _digest(password):
        salt = bytes(range(16))
        digest = hashlib.scrypt(password, salt=salt, n=16384, r=8, p=5, dklen=32)
        return salt, digest

    def test_password_hash_base64_matches_maghes_private_config(self):
        salt, digest = self._digest(b"example-only")
        encoded = (
            "scrypt$16384$8$5$"
            + base64.b64encode(salt).decode()
            + "$"
            + base64.b64encode(digest).decode()
        )
        accounts = {"up3": {"password_hash": encoded,
                            "schema": "cilacap_5221", "role": "viewer"}}
        self.assertIsNotNone(authenticate(accounts, "up3", "example-only"))
        self.assertIsNone(authenticate(accounts, "up3", "wrong"))
        self.assertIsNone(authenticate(accounts, "unknown", "example-only"))

    def test_legacy_hex_password_hash_remains_supported(self):
        salt, digest = self._digest(b"example-only")
        encoded = "scrypt$16384$8$5$" + salt.hex() + "$" + digest.hex()
        accounts = {"up3": {"password_hash": encoded,
                            "schema": "cilacap_5221", "role": "viewer"}}
        self.assertIsNotNone(authenticate(accounts, "up3", "example-only"))

    def test_result_month_uses_data_period_not_publish_date(self):
        self.assertEqual(table_month("202610_ADD_APP"), "202610")
        self.assertEqual(table_month("20261023_ADD_TIANG_SEMARANG"), "202610")
        self.assertEqual(table_month("202609_ADD_APP"), "202609")
        self.assertIsNone(table_month("MASTER_APP"))
        self.assertIsNone(table_month("202613_ADD_APP"))

    def test_submission_scope(self):
        self.assertEqual(assigned_schemas("viewer", "semarang_5217,cilacap_5221"),
                         ["semarang_5217"])

    def test_table_name_is_built_from_month_and_allowed_asset(self):
        self.assertEqual(build_table_name("202610", "gardu_distribusi"),
                         "202610_ADD_GARDU_DISTRIBUSI")
        self.assertIn("STLTR", ASSET_TYPES)
        with self.assertRaises(ValueError):
            build_table_name("202613", "APP")
        with self.assertRaises(ValueError):
            build_table_name("202610", "TABEL_BEBAS")

    def test_rejects_another_up3_before_database_write(self):
        engine = MagicMock()
        account = {"schema": "semarang_5217", "role": "viewer", "email": "example@example.com"}
        with self.assertRaises(ValueError):
            submit_request(engine, "up3", account, "cilacap_5221",
                           "202610_ADD_APP", 42, "")
        engine.begin.assert_not_called()

    def test_insert_returns_request_id(self):
        engine = MagicMock()
        engine.begin.return_value.__enter__.return_value.execute.return_value.scalar_one_or_none.return_value = "request-id"
        account = {"schema": "semarang_5217", "role": "viewer", "email": "example@example.com"}
        request_id = submit_request(engine, "up3", account, "semarang_5217",
                                    "202610_ADD_APP", 42, "")
        self.assertEqual(len(request_id), 36)
        self.assertEqual(
            engine.begin.return_value.__enter__.return_value.execute.call_args.args[1]["table"],
            "202610_ADD_APP",
        )

    def test_multiple_asset_requests_share_one_transaction(self):
        engine = MagicMock()
        connection = engine.begin.return_value.__enter__.return_value
        first, second = MagicMock(), MagicMock()
        first.scalar_one_or_none.return_value = "first"
        second.scalar_one_or_none.return_value = "second"
        connection.execute.side_effect = [first, second]
        account = {"schema": "semarang_5217", "role": "viewer", "email": "example@example.com"}

        requests = submit_requests(
            engine, "up3", account, "semarang_5217",
            ["202610_ADD_APP", "202610_ADD_TRAFO"], "unggahan lengkap"
        )

        self.assertEqual(len(requests), 2)
        self.assertEqual(engine.begin.call_count, 1)
        submitted_tables = [call.args[1]["table"] for call in connection.execute.call_args_list]
        self.assertEqual(submitted_tables, ["202610_ADD_APP", "202610_ADD_TRAFO"])


if __name__ == "__main__":
    unittest.main()
