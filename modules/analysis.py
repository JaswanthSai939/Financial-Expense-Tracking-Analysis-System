import pandas as pd


EXPENSE_COLUMNS = [
    "Expense_ID",
    "User_ID",
    "Amount",
    "Category",
    "Description",
    "Date",
    "Payment_Mode",
    "Month",
]


def prepare_expense_frame(df):
    if df.empty:
        return pd.DataFrame(columns=EXPENSE_COLUMNS)

    prepared = df.copy()
    for column in EXPENSE_COLUMNS:
        if column != "Month" and column not in prepared.columns:
            prepared[column] = None

    prepared["Amount"] = pd.to_numeric(prepared["Amount"], errors="coerce").fillna(0)
    prepared["Date"] = pd.to_datetime(prepared["Date"])
    prepared["Month"] = prepared["Date"].dt.to_period("M").astype(str)
    return prepared[EXPENSE_COLUMNS]


def calculate_summary(df):
    if df.empty:
        return {
            "total": 0,
            "average": 0,
            "highest_category": "No data",
            "current_month": 0,
            "previous_month": 0,
            "change": 0,
        }

    prepared = prepare_expense_frame(df)
    monthly = prepared.groupby("Month")["Amount"].sum().sort_index()
    category = prepared.groupby("Category")["Amount"].sum().sort_values(ascending=False)

    current_month = float(monthly.iloc[-1]) if len(monthly) else 0
    previous_month = float(monthly.iloc[-2]) if len(monthly) >= 2 else 0

    return {
        "total": float(prepared["Amount"].sum()),
        "average": float(prepared["Amount"].mean()),
        "highest_category": category.index[0] if len(category) else "No data",
        "current_month": current_month,
        "previous_month": previous_month,
        "change": current_month - previous_month,
    }


def monthly_expenses(df):
    prepared = prepare_expense_frame(df)
    if prepared.empty:
        return pd.DataFrame(columns=["Month", "Amount"])
    return prepared.groupby("Month", as_index=False)["Amount"].sum().sort_values("Month")


def category_expenses(df):
    prepared = prepare_expense_frame(df)
    if prepared.empty:
        return pd.DataFrame(columns=["Category", "Amount"])
    return prepared.groupby("Category", as_index=False)["Amount"].sum().sort_values("Amount", ascending=False)
