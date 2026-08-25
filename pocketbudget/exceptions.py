"""Custom domain exceptions."""


class PocketBudgetError(Exception):
    """Base class for all PocketBudget domain errors."""


class InvalidCategoryError(PocketBudgetError):
    """Raised when an expense uses a category that is not allowed."""


class InsufficientFundsError(PocketBudgetError):
    """Raised when an expense exceeds the account balance."""
