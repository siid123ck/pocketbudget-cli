"""Feature Build 8: specific exceptions, atomic batches, crash-proof CLI."""

from pathlib import Path

import pytest

from pocketbudget.account import Account
from pocketbudget.cli import main
from pocketbudget.exceptions import (
    CorruptedStorageError,
    InsufficientFundsError,
    InvalidAmountError,
    InvalidCategoryError,
)


class TestSpecificExceptions:
    def test_negative_income_raises_domain_exception(self) -> None:
        account = Account(balance=100.0)
        with pytest.raises(InvalidAmountError):
            account.add_income(-50.0)

    def test_domain_amount_error_remains_value_error_compatible(self) -> None:
        assert issubclass(InvalidAmountError, ValueError)

    def test_zero_expense_raises_domain_exception(self) -> None:
        account = Account(balance=100.0)
        with pytest.raises(InvalidAmountError):
            account.add_expense(0, "Food")

    def test_non_positive_budget_limit_raises_domain_exception(self) -> None:
        account = Account()
        with pytest.raises(InvalidAmountError):
            account.set_budget("Food", -10.0)

    def test_negative_initial_balance_raises_domain_exception(self) -> None:
        with pytest.raises(InvalidAmountError):
            Account(balance=-5.0)

    def test_rule_exceptions_are_mutually_distinguishable(self) -> None:
        assert not issubclass(InsufficientFundsError, InvalidCategoryError)
        assert not issubclass(InvalidCategoryError, InsufficientFundsError)
        assert not issubclass(CorruptedStorageError, InvalidAmountError)


class TestAllOrNothingBatch:
    def test_valid_batch_applies_every_operation(self) -> None:
        account = Account(balance=100.0, budgets={"Food": 50.0})
        warnings = account.apply_batch(
            [("income", 200.0, "salary"), ("expense", 60.0, "food")]
        )
        assert warnings[0] is None
        assert warnings[1] is not None
        assert account.balance == 240.0
        assert len(account.get_transactions()) == 2

    def test_failed_midway_batch_leaves_state_untouched(self) -> None:
        account = Account(balance=100.0)
        with pytest.raises(InvalidAmountError):
            account.apply_batch(
                [
                    ("income", 500.0, "salary"),
                    ("expense", -20.0, "Food"),
                    ("expense", 10.0, "Transport"),
                ]
            )
        assert account.balance == 100.0
        assert account.get_transactions() == ()

    def test_batch_over_budget_warns_instead_of_blocking(self) -> None:
        account = Account(balance=300.0, budgets={"Food": 50.0})
        warnings = account.apply_batch([("expense", 80.0, "Food")])
        assert warnings[0] is not None
        assert account.balance == 220.0

    def test_empty_batch_changes_nothing(self) -> None:
        account = Account(balance=42.0)
        assert account.apply_batch([]) == ()
        assert account.balance == 42.0


class TestCliNeverShowsTracebacks:
    def test_negative_amount_becomes_clean_message(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "budget.json"
        code = main(["add-income", "-5", "salary"], path)
        assert code == 1
        captured = capsys.readouterr()
        assert "Traceback" not in captured.err
        assert "error" in captured.err.lower()

    def test_corrupted_save_file_becomes_clean_message(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "budget.json"
        path.write_text("{garbage", encoding="utf-8")
        code = main(["show-balance"], path)
        assert code == 1
        captured = capsys.readouterr()
        assert "Traceback" not in captured.out + captured.err
        assert "error" in captured.err.lower()

    def test_even_unexpected_errors_stay_clean(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def explode(path: object) -> Account:
            raise RuntimeError("disk on fire")

        monkeypatch.setattr("pocketbudget.cli.load_account", explode)
        code = main(["show-balance"], tmp_path / "budget.json")
        assert code == 1
        captured = capsys.readouterr()
        assert "Traceback" not in captured.out + captured.err
