# Application Domain Rules

This document is the source of truth for your TDD loop. Fill in each section **before** you write any code — every rule you write here becomes at least one test.

There are no wrong answers, but there are inconsistent ones. Once you decide a rule, your code has to match it.

---

## 1. Currency Symbol

*What currency does your application use, and how is money formatted when it's displayed?*

> **$** — all amounts are stored as floats and displayed formatted to 2 decimal places, e.g. `$12.50` (never negative by rule 3).

---

## 2. Standard Categories

*Which expense categories are allowed? Limit yourself to 3–5. What happens if someone uses a category that isn't on your list?*

> Exactly four categories are allowed: **Food**, **Transport**, **Utilities**, **Entertainment** (matched case-insensitively, e.g. `food` is valid). Any other category blocks the transaction with an `InvalidCategoryError`.

---

## 3. Overspending Behaviour (Total Balance)

*What happens when an expense is larger than the total balance? Does your app allow the balance to go negative, or does it block the transaction? If it blocks, what does the caller get back?*

> Blocked. The balance may **never** go negative: an expense greater than the current balance raises `InsufficientFundsError` and leaves the balance unchanged.

---

## 4. Budget Limits (Category Budgets)

*What happens when an expense exceeds a category's budget limit, but the balance could still cover it? Is it blocked, or is it recorded with a warning?*

> Recorded with a warning. The transaction succeeds and the balance is reduced, but the caller is warned (e.g. a returned warning message) that the **Food** budget limit has been exceeded. Budgets guide, they don't block.

---

## TDD Blueprint

Now turn each rule above into the test you will write **before** the implementation exists. Name the behaviour you'd assert.

- [x] Rule 1 (Currency) → `format_amount(10)` returns `"$10.00"` — money always renders as `$` + 2 decimals.
- [x] Rule 2 (Categories) → `add_expense(amount=5.0, category="fuel")` raises `InvalidCategoryError`; `"Food"` and `"food"` both succeed.
- [x] Rule 3 (Overspending) → spending more than the balance raises `InsufficientFundsError` and `balance` is unchanged afterwards.
- [x] Rule 4 (Budget Limits) → an expense over the category's budget still succeeds: balance decreases by the amount and an over-budget warning is surfaced to the caller.
