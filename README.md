# PocketBudget

A command-line budget tracker that treats your money data the way it deserves to be
treated: every transaction is validated, every balance change is auditable, and no
hand-edited save file can silently corrupt your account.

PocketBudget solves a simple problem — knowing where your money goes against per-category
spending limits — while demonstrating something less simple: how to build a small
application whose internal state *cannot* be put into an invalid condition from the outside.

## Features

- Income and expense recording with case-insensitive categories
  (`Food`, `Transport`, `Utilities`, `Entertainment`)
- Per-category budgets that **warn without blocking** — over-budget spending is still
  recorded, honestly flagged in `show-summary`
- Persistent JSON storage in `data/budget.json` with corruption and tamper detection
- A crash-proof CLI: invalid input produces a clean one-line error, never a traceback

## Installation & Setup

Requires Python 3.11+.

```bash
git clone https://github.com/siid123ck/pocketbudget-cli.git
cd pocketbudget-cli

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pre-commit install
```

## Usage

All commands follow the same lifecycle: load saved state → run the domain operation →
save the result. Your data survives between runs.

```bash
# Record income (any source label you like)
python -m pocketbudget.cli add-income 500 salary

# Set a spending ceiling for a category
python -m pocketbudget.cli set-budget food 100

# Record an expense — validated against balance and remaining budget
python -m pocketbudget.cli add-expense 120 food
# Added $120.00 expense (food). New balance: $380.00
# Warning: Food expense of $120.00 exceeds the remaining $100.00 of its $100.00 budget.

# Check where you stand
python -m pocketbudget.cli show-balance
python -m pocketbudget.cli show-history
python -m pocketbudget.cli show-summary
```

`show-summary` renders each budgeted category as a progress bar:

```
Food             $120.00 / $100.00   [##########]  OVER!
```

Invalid input fails cleanly and leaves your saved state untouched:

```bash
$ python -m pocketbudget.cli add-expense 999 food
error: Expense of $999.00 exceeds balance of $0.00.
```

## Running the Tests

```bash
pytest tests/ -v
```

74 tests cover the domain rules, transaction history immutability, storage round-trips,
budget behaviour, CLI output, and error handling — all green means every guarantee below
still holds. Linting, formatting, strict typing, and complexity limits (≤ 7) run
automatically on every commit via pre-commit; to check everything at once:

```bash
pre-commit run --all-files
```

## Design Decisions

The core question of this project: *how do you stop outside code — including your own
future mistakes — from corrupting financial state?*

**The balance is readable but not writable.** `Account.balance` is a property with a
getter and deliberately no setter. Python then does the enforcement for free:
`account.balance = 500` raises `AttributeError`. A leading underscore alone
(`self._balance`) is only a naming convention; the property is the mechanism that
actually blocks assignment.

**The history can't be mutated through the back door.** `get_transactions()` returns a
tuple, not the internal list — `.clear()`, `.append()` and `.pop()` on it fail loudly.
Each record is itself a frozen dataclass, so even field tampering
(`tx.amount = 9999`) raises. I chose a tuple over returning a copy because copies still
leak mutable elements; immutability has to hold all the way down.

**Every mutation passes through one gateway.** The only ways to move money are
`add_income()` and `add_expense()`, and they validate *before* touching state — amount,
category, then funds — so a rejected transaction leaves the balance exactly as it was.
There is no method that sets the balance directly, because "just this once" is how
corruption starts.

**Disk data gets the same suspicion as keyboard input.** Loading never writes parsed
values into private fields. Instead, `Account.from_history()` replays saved records
through the exact same public methods a live user would hit, so a negative amount or
unknown category inside a hand-edited file trips the identical validations. On top of
that, the stored balance must equal opening balance + Σ(history) or the file is rejected
as tampered — a wrong number cannot slip through as long as the history doesn't agree
with it.

**Rules live in the domain, not the interface.** The CLI parses arguments, calls domain
methods, and prints results — it contains zero budgeting logic and never checks an
amount or limit. That's why the same rule set works identically from the terminal, in
tests, and anywhere else the classes get reused.

**Budgets guide, they don't block.** Per `rules.md` (the committed spec this project was
built against), overspending the *balance* raises `InsufficientFundsError`, but exceeding
a category *budget* records the expense with a warning. Blocking would hide what
actually happened; a warning keeps the ledger truthful while still surfacing the
problem.

**Failures are specific and atomic.** Each broken rule raises its own exception type
(`InvalidAmountError`, `InvalidCategoryError`, `InsufficientFundsError`,
`CorruptedStorageError`), and `apply_batch()` proves the all-or-nothing property: the
batch runs against a trial copy first, so a failure midway leaves the real account
byte-for-byte unchanged.
