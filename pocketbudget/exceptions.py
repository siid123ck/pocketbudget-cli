"""Custom domain exceptions."""


class PocketBudgetError(Exception):
    """Base class for all PocketBudget domain errors."""


class InvalidAmountError(PocketBudgetError, ValueError):
    """Raised when an amount or limit is not a valid positive number."""


class InvalidCategoryError(PocketBudgetError):
    """Raised when an expense uses a category that is not allowed."""


class InsufficientFundsError(PocketBudgetError):
    """Raised when an expense exceeds the account balance."""


class CorruptedStorageError(PocketBudgetError):
    """Raised when a save file is unreadable, malformed, or inconsistent."""
