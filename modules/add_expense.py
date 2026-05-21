from database.db import add_expense as add_expense_to_mysql


CATEGORIES = [
    "Food",
    "Travel",
    "Shopping",
    "Bills",
    "Entertainment",
    "Health",
    "Education",
    "Rent",
    "Savings",
    "Other",
]

PAYMENT_MODES = ["UPI", "Cash", "Card", "Net Banking", "Wallet"]


def save_expense(user_id, amount, category, description, expense_date, payment_mode):
    add_expense_to_mysql(user_id, amount, category, description, expense_date, payment_mode)
