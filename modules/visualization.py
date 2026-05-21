import plotly.express as px

from modules.analysis import category_expenses, monthly_expenses, prepare_expense_frame


def category_pie_chart(df):
    category_data = category_expenses(df)
    return px.pie(category_data, values="Amount", names="Category", hole=0.35)


def category_bar_chart(df):
    category_data = category_expenses(df)
    return px.bar(category_data, x="Category", y="Amount", color="Category")


def monthly_line_chart(df):
    monthly_data = monthly_expenses(df)
    return px.line(monthly_data, x="Month", y="Amount", markers=True)


def daily_trend_chart(df):
    prepared = prepare_expense_frame(df)
    return px.line(
        prepared.sort_values("Date"),
        x="Date",
        y="Amount",
        color="Category",
        markers=True,
    )
