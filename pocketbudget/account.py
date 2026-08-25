"""Domain: budgeting rules and protected account state."""

from datetime import date

from pocketbudget.exceptions import InsufficientFundsError, InvalidCategoryError
from pocketbudget.models import Transaction

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
        self._balance = float(balance)
        self._transactions: list[Transaction] = []
        self._budgets: dict[str, float] = {
            category.casefold(): limit for category, limit in (budgets or {}).items()
        }

    @property
    def balance(self) -> float:
        """Current balance (read-only)."""
        return self._balance

    def get_transactions(self) -> tuple[Transaction, ...]:
        """Read-only view of the history: a tuple of frozen records."""
        return tuple(self._transactions)

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
        self._transactions.append(
            Transaction(amount=amount, category=key, date=date.today())
        )
        return self._over_budget_warning(key, amount)

    @staticmethod
    def _validate_amount(amount: float) -> None:
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}.")

    def _over_budget_warning(self, category: str, amount: float) -> str | None:
        limit = self._budgets.get(category)
        if limit is not None and amount > limit:
            return (
                f"Warning: ${amount:.2f} exceeds the {category.title()} "
                f"budget of ${limit:.2f}."
            )
        return None
