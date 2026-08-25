"""Feature Build 4: transaction history with no mutability leak."""

import dataclasses
from datetime import date
from typing import Any, cast

import pytest

from pocketbudget.account import Account
from pocketbudget.exceptions import InsufficientFundsError


class TestEveryTransactionIsRecorded:
    def test_income_is_recorded_with_amount_category_and_date(self) -> None:
        account = Account(balance=100.0)
        account.add_income(50.0)
        history = account.get_transactions()
        assert len(history) == 1
        entry = history[0]
        assert entry.amount == 50.0
        assert entry.category == "income"
        assert entry.date == date.today()

    def test_expense_is_recorded_with_amount_category_and_date(self) -> None:
        account = Account(balance=100.0)
        account.add_expense(30.0, "Food")
        history = account.get_transactions()
        assert len(history) == 1
        entry = history[0]
        assert entry.amount == 30.0
        assert entry.category == "food"
        assert entry.date == date.today()

    def test_history_preserves_chronological_order(self) -> None:
        account = Account(balance=200.0)
        account.add_income(50.0)
        account.add_expense(20.0, "Transport")
        account.add_expense(10.0, "Utilities")
        categories = [tx.category for tx in account.get_transactions()]
        assert categories == ["income", "transport", "utilities"]

    def test_rejected_transactions_leave_no_trace(self) -> None:
        account = Account(balance=50.0)
        with pytest.raises(ValueError):
            account.add_income(-5.0)
        with pytest.raises(InsufficientFundsError):
            account.add_expense(60.0, "Food")
        assert account.get_transactions() == ()


class TestHistoryIsReadable:
    def test_empty_account_has_no_transactions(self) -> None:
        assert Account(balance=10.0).get_transactions() == ()

    def test_caller_can_read_full_history(self) -> None:
        account = Account(balance=100.0)
        account.add_income(40.0)
        account.add_expense(15.0, "Entertainment")
        history = account.get_transactions()
        assert [tx.amount for tx in history] == [40.0, 15.0]


class TestNoMutabilityLeak:
    def test_clearing_returned_history_does_not_affect_account(self) -> None:
        account = Account(balance=100.0)
        account.add_income(25.0)
        history = account.get_transactions()
        with pytest.raises(AttributeError):
            cast(Any, history).clear()
        assert len(account.get_transactions()) == 1

    def test_appending_to_returned_history_does_not_affect_account(self) -> None:
        account = Account(balance=100.0)
        account.add_income(25.0)
        history = account.get_transactions()
        with pytest.raises(AttributeError):
            cast(Any, history).append(object())
        assert len(account.get_transactions()) == 1

    def test_popping_returned_history_does_not_affect_account(self) -> None:
        account = Account(balance=100.0)
        account.add_income(25.0)
        account.add_expense(10.0, "Food")
        history = account.get_transactions()
        with pytest.raises(AttributeError):
            cast(Any, history).pop()
        assert len(account.get_transactions()) == 2

    def test_transaction_records_themselves_are_immutable(self) -> None:
        account = Account(balance=100.0)
        account.add_income(25.0)
        entry = account.get_transactions()[0]
        with pytest.raises(dataclasses.FrozenInstanceError):
            cast(Any, entry).amount = 9999.0
        assert account.get_transactions()[0].amount == 25.0
