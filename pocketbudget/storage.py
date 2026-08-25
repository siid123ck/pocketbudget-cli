"""Storage: saving and loading application state."""

import json
import math
from datetime import date
from pathlib import Path

from pocketbudget.account import Account
from pocketbudget.exceptions import CorruptedStorageError, PocketBudgetError
from pocketbudget.models import Transaction

DEFAULT_DATA_PATH: Path = Path("data") / "budget.json"


def save_account(account: Account, path: Path = DEFAULT_DATA_PATH) -> Path:
    """Write the account state to ``path`` (creating folders) and return it."""
    payload = {
        "balance": account.balance,
        "transactions": [
            {
                "amount": tx.amount,
                "category": tx.category,
                "date": tx.date.isoformat(),
            }
            for tx in account.get_transactions()
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_account(path: Path = DEFAULT_DATA_PATH) -> Account:
    """Rebuild an Account from ``path``.

    A missing file yields a clean, empty account. Existing content is
    treated with full suspicion: it must parse, have the right shape,
    pass every domain validation on replay, and its stored balance must
    agree with the history — otherwise :class:`CorruptedStorageError`.
    """
    if not path.exists():
        return Account()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("top-level JSON value must be an object.")
        saved_balance = float(payload["balance"])
        raw_transactions = payload["transactions"]
        if not isinstance(raw_transactions, list):
            raise TypeError("transactions must be a list.")
        history = [_parse_transaction(raw) for raw in raw_transactions]
        account = Account.from_history(history)
    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        PocketBudgetError,
    ) as err:
        raise CorruptedStorageError(f"Unusable save file {path}: {err}") from err

    if not math.isclose(account.balance, saved_balance, abs_tol=0.005):
        raise CorruptedStorageError(
            f"Saved balance {saved_balance} contradicts history "
            f"total {account.balance}."
        )
    return account


def _parse_transaction(raw: object) -> Transaction:
    if not isinstance(raw, dict):
        raise TypeError("each transaction must be an object.")
    amount = float(raw["amount"])
    category = raw["category"]
    if not isinstance(category, str):
        raise TypeError("transaction category must be a string.")
    day = date.fromisoformat(raw["date"]) if isinstance(raw["date"], str) else None
    if day is None:
        raise TypeError("transaction date must be an ISO string.")
    return Transaction(amount=amount, category=category, date=day)
