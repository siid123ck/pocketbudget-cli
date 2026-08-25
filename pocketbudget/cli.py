"""CLI: user input and command routing."""

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from pocketbudget.account import Account
from pocketbudget.exceptions import CorruptedStorageError, PocketBudgetError
from pocketbudget.storage import DEFAULT_DATA_PATH, load_account, save_account


def main(argv: list[str] | None = None, data_path: Path = DEFAULT_DATA_PATH) -> int:
    """Parse arguments, run one command lifecycle, return an exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        account = load_account(data_path)
    except CorruptedStorageError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    handler: Handler = args.func
    try:
        return handler(args, account, data_path)
    except (PocketBudgetError, ValueError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1


Handler = Callable[[argparse.Namespace, Account, Path], int]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pocketbudget", description="A safe little budget tracker."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    income = sub.add_parser("add-income", help="Record a deposit.")
    income.add_argument("amount", type=float)
    income.add_argument("category")
    income.set_defaults(func=_cmd_add_income)

    expense = sub.add_parser("add-expense", help="Record an expense.")
    expense.add_argument("amount", type=float)
    expense.add_argument("category")
    expense.set_defaults(func=_cmd_add_expense)

    balance = sub.add_parser("show-balance", help="Print the current balance.")
    balance.set_defaults(func=_cmd_show_balance)

    history = sub.add_parser("show-history", help="List all transactions.")
    history.set_defaults(func=_cmd_show_history)

    budget = sub.add_parser("set-budget", help="Set a category spending limit.")
    budget.add_argument("category")
    budget.add_argument("limit", type=float)
    budget.set_defaults(func=_cmd_set_budget)

    summary = sub.add_parser("show-summary", help="Spending vs budgets.")
    summary.set_defaults(func=_cmd_show_summary)

    return parser


def _cmd_add_income(args: argparse.Namespace, account: Account, path: Path) -> int:
    account.add_income(args.amount, args.category)
    save_account(account, path)
    print(
        f"Added {_fmt(args.amount)} income ({args.category.lower()}). "
        f"New balance: {_fmt(account.balance)}"
    )
    return 0


def _cmd_add_expense(args: argparse.Namespace, account: Account, path: Path) -> int:
    warning = account.add_expense(args.amount, args.category)
    save_account(account, path)
    print(
        f"Added {_fmt(args.amount)} expense ({args.category.lower()}). "
        f"New balance: {_fmt(account.balance)}"
    )
    if warning is not None:
        print(warning)
    return 0


def _cmd_show_balance(args: argparse.Namespace, account: Account, path: Path) -> int:
    print(f"Current balance: {_fmt(account.balance)}")
    return 0


def _cmd_show_history(args: argparse.Namespace, account: Account, path: Path) -> int:
    transactions = account.get_transactions()
    if not transactions:
        print("No transactions recorded yet.")
        return 0
    for tx in transactions:
        sign = "+" if tx.kind == "income" else "-"
        print(f"{tx.date.isoformat()}  {sign}{_fmt(tx.amount):>9}  {tx.category}")
    return 0


def _cmd_set_budget(args: argparse.Namespace, account: Account, path: Path) -> int:
    account.set_budget(args.category, args.limit)
    save_account(account, path)
    print(f"Budget for {args.category.lower()} set to {_fmt(args.limit)}")
    return 0


def _cmd_show_summary(args: argparse.Namespace, account: Account, path: Path) -> int:
    budgets = account.budgets
    if not budgets:
        print("No budgets set. Try: set-budget <category> <limit>")
        return 0
    for category in sorted(budgets):
        limit = budgets[category]
        remaining = account.remaining_budget(category) or 0.0
        spent = limit - remaining
        filled = round(max(min(spent / limit, 1.0), 0.0) * 10)
        bar = "#" * filled + "-" * (10 - filled)
        flag = "  OVER!" if remaining < 0 else ""
        print(
            f"{category.title():<14}{_fmt(spent):>10} / {_fmt(limit):<10}[{bar}]{flag}"
        )
    return 0


def _fmt(amount: float) -> str:
    return f"${amount:.2f}"


if __name__ == "__main__":
    raise SystemExit(main())
