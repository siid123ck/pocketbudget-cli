"""Feature Build 3: protected Account — one test per rule in rules.md."""

import pytest

from pocketbudget.account import Account
from pocketbudget.exceptions import InsufficientFundsError, InvalidCategoryError


class TestBalanceIsReadOnly:
    def test_balance_is_readable(self) -> None:
        account = Account(balance=100.0)
        assert account.balance == 100.0

    def test_balance_cannot_be_assigned_from_outside(self) -> None:
        account = Account(balance=100.0)
        with pytest.raises(AttributeError):
            setattr(account, "balance", 500.0)

    def test_failed_assignment_does_not_change_balance(self) -> None:
        account = Account(balance=100.0)
        with pytest.raises(AttributeError):
            setattr(account, "balance", 500.0)
        assert account.balance == 100.0


class TestControlledMutations:
    def test_add_income_increases_balance(self) -> None:
        account = Account(balance=100.0)
        account.add_income(50.0)
        assert account.balance == 150.0

    def test_add_expense_decreases_balance(self) -> None:
        account = Account(balance=100.0)
        account.add_expense(30.0, "Food")
        assert account.balance == 70.0


class TestTransactionValidation:
    def test_negative_income_is_rejected(self) -> None:
        account = Account(balance=100.0)
        with pytest.raises(ValueError):
            account.add_income(-50.0)

    def test_rejected_income_leaves_balance_unchanged(self) -> None:
        account = Account(balance=100.0)
        with pytest.raises(ValueError):
            account.add_income(-50.0)
        assert account.balance == 100.0

    def test_negative_expense_is_rejected(self) -> None:
        account = Account(balance=100.0)
        with pytest.raises(ValueError):
            account.add_expense(-20.0, "Food")

    def test_rejected_expense_leaves_balance_unchanged(self) -> None:
        account = Account(balance=100.0)
        with pytest.raises(ValueError):
            account.add_expense(-20.0, "Food")
        assert account.balance == 100.0


class TestOverdraftBlockedPerRules:
    def test_expense_larger_than_balance_raises_insufficient_funds_error(
        self,
    ) -> None:
        account = Account(balance=50.0)
        with pytest.raises(InsufficientFundsError):
            account.add_expense(60.0, "Food")

    def test_blocked_overdraft_leaves_balance_unchanged(self) -> None:
        account = Account(balance=50.0)
        with pytest.raises(InsufficientFundsError):
            account.add_expense(60.0, "Food")
        assert account.balance == 50.0


class TestCategoryRules:
    def test_unknown_category_is_rejected(self) -> None:
        account = Account(balance=100.0)
        with pytest.raises(InvalidCategoryError):
            account.add_expense(10.0, "fuel")

    def test_categories_match_case_insensitively(self) -> None:
        account = Account(balance=100.0)
        account.add_expense(10.0, "food")
        assert account.balance == 90.0


class TestBudgetLimitWarning:
    def test_expense_over_category_budget_still_records_with_warning(
        self,
    ) -> None:
        account = Account(
            balance=200.0,
            budgets={"Food": 100.0},
        )
        warning = account.add_expense(120.0, "Food")
        assert warning is not None
        assert "budget" in warning.lower()
        assert account.balance == 80.0

    def test_expense_within_budget_returns_no_warning(self) -> None:
        account = Account(
            balance=200.0,
            budgets={"Food": 100.0},
        )
        warning = account.add_expense(80.0, "Food")
        assert warning is None
