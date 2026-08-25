"""Domain: budgeting rules and protected account state."""

from collections.abc import Sequence
from datetime import date

from pocketbudget.exceptions import InsufficientFundsError, InvalidCategoryError
from pocketbudget.models import Transaction

INCOME_CATEGORY = "income"
ALLOWED_CATEGORIES: frozenset[str] = frozenset(
    {"food", "transport", "utilities", "entertainment"}
)


class Account:
    """Single source of truth for the balance.

    The balance is readable from outside but never assignable:
    ``balance`` is a property with a getter and no setter, so
    ``account.balance = 500`` raises ``AttributeError``. All state
    changes go through :meth:`add_income` and :meth:`add_expense`.
    """

    def __init__(
        self, balance: float = 0.0, budgets: dict[str, float] | None = None
    ) -> None:
        if balance < 0:
            raise ValueError("Initial balance cannot be negative.")
        self._opening_balance = float(balance)
        self._balance = float(balance)
        self._transactions: list[Transaction] = []
        self._budgets: dict[str, float] = {}
        for category, limit in (budgets or {}).items():
            self.set_budget(category, limit)

    @property
    def balance(self) -> float:
        """Current balance (read-only)."""
        return self._balance

    @property
    def opening_balance(self) -> float:
        """Balance the account started with, before any transaction."""
        return self._opening_balance

    @property
    def budgets(self) -> dict[str, float]:
        """Copy of the configured limits by normalized category."""
        return dict(self._budgets)

    def set_budget(self, category: str, limit: float) -> None:
        """Set a spending limit for an allowed category."""
        key = category.casefold()
        if key not in ALLOWED_CATEGORIES:
            raise InvalidCategoryError(
                f"Unknown category {category!r}. Allowed: {sorted(ALLOWED_CATEGORIES)}"
            )
        if limit <= 0:
            raise ValueError(f"Budget limit must be positive, got {limit}.")
        self._budgets[key] = float(limit)

    def remaining_budget(self, category: str) -> float | None:
        """Limit minus recorded spending for the category; None if unset."""
        limit = self._budgets.get(category.casefold())
        if limit is None:
            return None
        return limit - self._spent_in(category.casefold())

    def _spent_in(self, category: str) -> float:
        return sum(tx.amount for tx in self._transactions if tx.category == category)

    def get_transactions(self) -> tuple[Transaction, ...]:
        """Read-only view of the history: a tuple of frozen records."""
        return tuple(self._transactions)

    @classmethod
    def from_history(
        cls,
        transactions: Sequence[Transaction],
        budgets: dict[str, float] | None = None,
        opening_balance: float = 0.0,
    ) -> "Account":
        """Build an account by replaying records through the public API.

        Every record is validated exactly like live user input; the
        only difference is that historical dates are preserved instead
        of being re-stamped with today's date.
        """
        account = cls(balance=opening_balance, budgets=budgets)
        for tx in transactions:
            if tx.category == INCOME_CATEGORY:
                account.add_income(tx.amount)
            else:
                account.add_expense(tx.amount, tx.category)
            account._transactions[-1] = tx
        return account

    def add_income(self, amount: float) -> None:
        """Add a positive amount to the balance and record it."""
        self._validate_amount(amount)
        self._balance += amount
        self._transactions.append(
            Transaction(amount=amount, category="income", date=date.today())
        )

    def add_expense(self, amount: float, category: str) -> str | None:
        """Record an expense; returns an over-budget warning or ``None``."""
        self._validate_amount(amount)
        key = category.casefold()
        if key not in ALLOWED_CATEGORIES:
            raise InvalidCategoryError(
                f"Unknown category {category!r}. Allowed: {sorted(ALLOWED_CATEGORIES)}"
            )
        if amount > self._balance:
            raise InsufficientFundsError(
                f"Expense of ${amount:.2f} exceeds balance of ${self._balance:.2f}."
            )
        self._balance -= amount
        warning = self._over_budget_warning(key, amount)
        self._transactions.append(
            Transaction(amount=amount, category=key, date=date.today())
        )
        return warning

    @staticmethod
    def _validate_amount(amount: float) -> None:
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}.")

    def _over_budget_warning(self, category: str, amount: float) -> str | None:
        limit = self._budgets.get(category)
        if limit is None:
            return None
        remaining = limit - self._spent_in(category)
        if amount > remaining:
            return (
                f"Warning: {category.title()} expense of ${amount:.2f} exceeds "
                f"the remaining ${remaining:.2f} of its ${limit:.2f} budget."
            )
        return None
