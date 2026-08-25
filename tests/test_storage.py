"""Feature Build 5: persistence that never bypasses Account validation."""

import json
from datetime import date
from pathlib import Path

import pytest

from pocketbudget.account import Account
from pocketbudget.exceptions import CorruptedStorageError
from pocketbudget.storage import load_account, save_account


def _sample_account() -> Account:
    account = Account()
    account.add_income(250.0)
    account.add_expense(40.0, "Food")
    account.add_expense(60.0, "transport")
    return account


class TestSaving:
    def test_save_writes_parseable_json_with_state(self, tmp_path: Path) -> None:
        target = tmp_path / "budget.json"
        save_account(_sample_account(), target)
        payload = json.loads(target.read_text(encoding="utf-8"))
        assert payload["balance"] == 150.0
        categories = [tx["category"] for tx in payload["transactions"]]
        assert categories == ["income", "food", "transport"]

    def test_save_creates_missing_data_folder(self, tmp_path: Path) -> None:
        target = tmp_path / "data" / "nested" / "budget.json"
        save_account(_sample_account(), target)
        assert target.exists()


class TestLoading:
    def test_roundtrip_restores_balance_and_history(self, tmp_path: Path) -> None:
        original = _sample_account()
        target = tmp_path / "budget.json"
        save_account(original, target)

        loaded = load_account(target)

        assert isinstance(loaded, Account)
        assert loaded.balance == original.balance
        assert loaded.get_transactions() == original.get_transactions()

    def test_transaction_dates_survive_the_roundtrip(self, tmp_path: Path) -> None:
        target = tmp_path / "budget.json"
        save_account(_sample_account(), target)
        loaded = load_account(target)
        assert all(tx.date == date.today() for tx in loaded.get_transactions())


class TestMissingFile:
    def test_missing_file_yields_clean_empty_account(self, tmp_path: Path) -> None:
        loaded = load_account(tmp_path / "does-not-exist.json")
        assert loaded.balance == 0.0
        assert loaded.get_transactions() == ()


class TestCorruptedFiles:
    def test_garbage_content_raises_domain_error(self, tmp_path: Path) -> None:
        target = tmp_path / "budget.json"
        target.write_text("{definitely not json", encoding="utf-8")
        with pytest.raises(CorruptedStorageError):
            load_account(target)

    def test_wrong_structure_raises_domain_error(self, tmp_path: Path) -> None:
        target = tmp_path / "budget.json"
        target.write_text(json.dumps({"foo": 1}), encoding="utf-8")
        with pytest.raises(CorruptedStorageError):
            load_account(target)

    def test_tampered_balance_is_detected(self, tmp_path: Path) -> None:
        target = tmp_path / "budget.json"
        target.write_text(
            json.dumps({"balance": 99999.0, "transactions": []}),
            encoding="utf-8",
        )
        with pytest.raises(CorruptedStorageError):
            load_account(target)

    def test_negative_amount_in_file_fails_validation(self, tmp_path: Path) -> None:
        target = tmp_path / "budget.json"
        target.write_text(
            json.dumps(
                {
                    "balance": -50.0,
                    "transactions": [
                        {"amount": -50.0, "category": "income", "date": "2026-08-25"}
                    ],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(CorruptedStorageError):
            load_account(target)

    def test_unknown_category_in_file_fails_validation(self, tmp_path: Path) -> None:
        target = tmp_path / "budget.json"
        target.write_text(
            json.dumps(
                {
                    "balance": 10.0,
                    "transactions": [
                        {"amount": 10.0, "category": "crypto", "date": "2026-08-25"}
                    ],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(CorruptedStorageError):
            load_account(target)
