"""Domain models shared across the application."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Transaction:
    """An immutable, dated financial event."""

    amount: float
    category: str
    date: date
