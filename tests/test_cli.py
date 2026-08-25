"""Feature Build 7: dumb CLI wiring commands to domain and storage."""

from collections.abc import Callable
from pathlib import Path

import pytest

from pocketbudget.account import Account
from pocketbudget.cli import main
from pocketbudget.storage import load_account, save_account


def _seed(
    balance: float = 100.0, budgets: dict[str, float] | None = None
) -> Callable[[Path], Account]:
    def factory(path: Path) -> Account:
        account = Account(balance=balance, budgets=budgets)
        save_account(account, path)
        return account

    return factory


class TestAddIncome:
    def test_records_income_and_persists(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "budget.json"
        code = main(["add-income", "50", "salary"], path)
        assert code == 0
        loaded = load_account(path)
        assert loaded.balance == 50.0
        assert loaded.get_transactions()[0].category == "salary"
        assert "50.00" in capsys.readouterr().out


class TestAddExpense:
    def test_records_expense_and_persists(self, tmp_path: Path) -> None:
        path = tmp_path / "budget.json"
        _seed()(path)
        code = main(["add-expense", "30", "Food"], path)
        assert code == 0
        assert load_account(path).balance == 70.0

    def test_over_budget_expense_prints_warning_but_succeeds(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "budget.json"
        _seed(budgets={"Food": 20.0})(path)
        code = main(["add-expense", "30", "food"], path)
        assert code == 0
        assert "budget" in capsys.readouterr().out.lower()

    def test_insufficient_funds_exits_nonzero_with_message(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "budget.json"
        _seed()(path)
        code = main(["add-expense", "999", "Food"], path)
        assert code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()
        assert load_account(path).balance == 100.0

    def test_invalid_category_exits_nonzero_with_message(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "budget.json"
        _seed()(path)
        code = main(["add-expense", "10", "crypto"], path)
        assert code == 1
        assert "error" in capsys.readouterr().err.lower()


class TestShowBalance:
    def test_prints_formatted_balance(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "budget.json"
        _seed(balance=123.5)(path)
        assert main(["show-balance"], path) == 0
        assert "$123.50" in capsys.readouterr().out


class TestShowHistory:
    def test_lists_recorded_transactions(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "budget.json"
        _seed()(path)
        main(["add-income", "40", "salary"], path)
        main(["add-expense", "15", "Entertainment"], path)
        capsys.readouterr()
        assert main(["show-history"], path) == 0
        out = capsys.readouterr().out.lower()
        assert "salary" in out
        assert "entertainment" in out
        assert "40.00" in out
        assert "15.00" in out


class TestSetBudget:
    def test_sets_limit_and_persists(self, tmp_path: Path) -> None:
        path = tmp_path / "budget.json"
        _seed()(path)
        assert main(["set-budget", "food", "200"], path) == 0
        assert load_account(path).remaining_budget("food") == 200.0

    def test_unknown_category_exits_nonzero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "budget.json"
        _seed()(path)
        assert main(["set-budget", "crypto", "200"], path) == 1
        assert "error" in capsys.readouterr().err.lower()


class TestShowSummary:
    def test_visualizes_spending_against_budgets(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "budget.json"
        _seed(budgets={"Food": 100.0})(path)
        main(["add-expense", "25", "food"], path)
        capsys.readouterr()
        assert main(["show-summary"], path) == 0
        out = capsys.readouterr().out
        assert "Food" in out
        assert "$25.00" in out
        assert "$100.00" in out


class TestLifecycle:
    def test_state_survives_across_separate_invocations(self, tmp_path: Path) -> None:
        path = tmp_path / "budget.json"
        main(["add-income", "100", "salary"], path)
        main(["add-expense", "40", "Transport"], path)
        account = load_account(path)
        assert account.balance == 60.0
        assert len(account.get_transactions()) == 2
