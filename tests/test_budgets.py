"""Feature Build 6: category budgets, decided entirely in the domain."""

import json
from pathlib import Path

import pytest

from pocketbudget.account import Account
from pocketbudget.exceptions import CorruptedStorageError, InvalidCategoryError
from pocketbudget.storage import load_account, save_account


class TestSettingBudgets:
    def test_limit_can_be_set_for_a_category(self) -> None:
        account = Account(balance=500.0)
        account.set_budget("Food", 200.0)
        assert account.remaining_budget("food") == 200.0

    def test_set_budget_matches_case_insensitively(self) -> None:
        account = Account(balance=500.0)
        account.set_budget("ENTERTAINMENT", 75.0)
        assert account.remaining_budget("entertainment") == 75.0

    def test_set_budget_rejects_unknown_category(self) -> None:
        account = Account(balance=500.0)
        with pytest.raises(InvalidCategoryError):
            account.set_budget("crypto", 100.0)

    @pytest.mark.parametrize("limit", [0, -25.0])
    def test_set_budget_rejects_non_positive_limits(self, limit: float) -> None:
        account = Account(balance=500.0)
        with pytest.raises(ValueError):
            account.set_budget("Food", limit)


class TestRemainingBudget:
    def test_no_budget_means_none(self) -> None:
        account = Account(balance=500.0)
        assert account.remaining_budget("Food") is None

    def test_spending_reduces_the_remaining_budget(self) -> None:
        account = Account(balance=500.0)
        account.set_budget("Food", 100.0)
        account.add_expense(40.0, "food")
        assert account.remaining_budget("Food") == 60.0

    def test_other_categories_do_not_touch_the_remaining(self) -> None:
        account = Account(balance=500.0)
        account.set_budget("Food", 100.0)
        account.add_expense(90.0, "Transport")
        assert account.remaining_budget("Food") == 100.0


class TestOverBudgetWarningNeverBlocks:
    def test_expense_past_remaining_records_with_warning(self) -> None:
        account = Account(balance=500.0)
        account.set_budget("Food", 50.0)
        assert account.add_expense(30.0, "Food") is None
        warning = account.add_expense(30.0, "Food")
        assert warning is not None
        assert "budget" in warning.lower()

    def test_warned_expenses_still_reduce_balance_and_history(self) -> None:
        account = Account(balance=500.0)
        account.set_budget("Food", 50.0)
        account.add_expense(30.0, "Food")
        account.add_expense(30.0, "Food")
        assert account.balance == 440.0
        assert len(account.get_transactions()) == 2

    def test_exact_fit_does_not_warn(self) -> None:
        account = Account(balance=500.0)
        account.set_budget("Food", 100.0)
        assert account.add_expense(100.0, "Food") is None


class TestBudgetsSurvivePersistence:
    def test_roundtrip_restores_budgets_and_warnings(self, tmp_path: Path) -> None:
        original = Account(balance=300.0)
        original.set_budget("Food", 50.0)
        target = tmp_path / "budget.json"
        save_account(original, target)

        loaded = load_account(target)

        assert loaded.remaining_budget("food") == 50.0
        assert loaded.add_expense(60.0, "Food") is not None

    def test_old_files_without_budgets_still_load(self, tmp_path: Path) -> None:
        target = tmp_path / "budget.json"
        target.write_text(
            json.dumps(
                {
                    "balance": 10.0,
                    "transactions": [
                        {"amount": 10.0, "category": "income", "date": "2026-08-25"}
                    ],
                }
            ),
            encoding="utf-8",
        )
        loaded = load_account(target)
        assert loaded.balance == 10.0
        assert loaded.remaining_budget("food") is None

    def test_corrupted_budget_value_is_rejected(self, tmp_path: Path) -> None:
        target = tmp_path / "budget.json"
        target.write_text(
            json.dumps(
                {
                    "balance": 0.0,
                    "transactions": [],
                    "budgets": {"food": -5},
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(CorruptedStorageError):
            load_account(target)
