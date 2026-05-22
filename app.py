from datetime import date
import os
from pathlib import Path
import secrets

import pandas as pd
import plotly.express as px
import streamlit as st

from auth.google_oauth import build_google_auth_url, fetch_google_user, login_or_create_google_user
from auth.login import authenticate_user
from auth.register import register_user
from database.db import (
    alert_already_sent,
    fetch_budget,
    fetch_budgets,
    fetch_expenses,
    fetch_users,
    initialize_database,
    mysql_available,
    record_alert_sent,
    upsert_budget,
)
from modules.add_expense import CATEGORIES, PAYMENT_MODES, save_expense
from modules.analysis import calculate_summary, category_expenses, monthly_expenses, prepare_expense_frame
from modules.email_alert import EmailDeliveryError, build_alert_message, expense_increased, send_alert_email
from modules.prediction import predict_next_month_expense
from modules.visualization import category_bar_chart, category_pie_chart, daily_trend_chart, monthly_line_chart


BASE_DIR = Path(__file__).parent
DATASET_PATH = BASE_DIR / "expenses_dataset.csv"
ENV_PATH = BASE_DIR / ".env"


st.set_page_config(
    page_title="Financial Expense Tracker",
    page_icon=":moneybag:",
    layout="wide",
)


def format_money(value):
    return f"Rs. {float(value):,.2f}"


def load_local_env():
    if not ENV_PATH.exists():
        return

    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_smtp_config():
    load_local_env()
    sender_email = os.getenv("SMTP_EMAIL", "")
    app_password = os.getenv("SMTP_APP_PASSWORD", "")

    try:
        sender_email = sender_email or st.secrets.get("SMTP_EMAIL", "")
        app_password = app_password or st.secrets.get("SMTP_APP_PASSWORD", "")
    except Exception:
        pass

    return sender_email, app_password


def get_resend_config():
    load_local_env()
    api_key = os.getenv("RESEND_API_KEY", "")
    from_email = os.getenv("RESEND_FROM_EMAIL", "")

    try:
        api_key = api_key or st.secrets.get("RESEND_API_KEY", "")
        from_email = from_email or st.secrets.get("RESEND_FROM_EMAIL", "")
    except Exception:
        pass

    return api_key, from_email


def get_google_oauth_config():
    load_local_env()
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")

    try:
        client_id = client_id or st.secrets.get("GOOGLE_CLIENT_ID", "")
        client_secret = client_secret or st.secrets.get("GOOGLE_CLIENT_SECRET", "")
        redirect_uri = st.secrets.get("GOOGLE_REDIRECT_URI", redirect_uri)
    except Exception:
        pass

    return client_id, client_secret, redirect_uri


def load_sample_data():
    df = pd.read_csv(DATASET_PATH)
    df = df.rename(columns={"Expense_ID": "Expense_ID"})
    df["User_ID"] = 1
    return df[["Expense_ID", "User_ID", "Amount", "Category", "Description", "Date", "Payment_Mode"]]


def get_expense_data(db_ready):
    if db_ready and st.session_state.get("user"):
        df = fetch_expenses(st.session_state["user"]["id"])
    else:
        df = load_sample_data()

    session_expenses = st.session_state.get("demo_expenses", [])
    if session_expenses:
        df = pd.concat([df, pd.DataFrame(session_expenses)], ignore_index=True)

    return prepare_expense_frame(df)


def init_session():
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("token", None)
    st.session_state.setdefault("demo_expenses", [])
    st.session_state.setdefault("auth_page", "Login")
    st.session_state.setdefault("oauth_state", None)


def handle_google_oauth_callback():
    params = st.query_params
    if "error" in params:
        st.error(f"Google login failed: {params['error']}")
        st.query_params.clear()
        return

    if "code" not in params:
        return

    client_id, client_secret, redirect_uri = get_google_oauth_config()
    if not client_id or not client_secret:
        st.error("Google OAuth is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env.")
        st.query_params.clear()
        return

    returned_state = params.get("state")
    expected_state = st.session_state.get("oauth_state")
    if expected_state and returned_state != expected_state:
        st.error("Google login state verification failed. Please try again.")
        st.query_params.clear()
        return

    try:
        google_user = fetch_google_user(params["code"], client_id, client_secret, redirect_uri)
        user, token = login_or_create_google_user(google_user)
        st.session_state["user"] = user
        st.session_state["token"] = token
        st.session_state["oauth_state"] = None
        st.query_params.clear()
        st.success("Google login successful.")
        st.rerun()
    except Exception as exc:
        st.query_params.clear()
        st.error(f"Google login failed: {exc}")


def render_auth_pages(db_ready):
    render_header(db_ready)
    handle_google_oauth_callback()

    if not db_ready:
        st.info("MySQL is not connected. You can open demo mode, but login/register requires MySQL.")
        if st.button("Continue Demo"):
            st.session_state["user"] = {
                "id": 1,
                "username": "Demo User",
                "email": "demo@example.com",
            }
            st.session_state["token"] = "demo-token"
            st.rerun()
        return

    with st.sidebar:
        st.header("Authentication")
        st.session_state["auth_page"] = st.radio("Page", ["Login", "Register"])

    if st.session_state["auth_page"] == "Login":
        st.subheader("Login")
        client_id, client_secret, redirect_uri = get_google_oauth_config()
        if client_id and client_secret:
            if not st.session_state["oauth_state"]:
                st.session_state["oauth_state"] = secrets.token_urlsafe(24)
            auth_url = build_google_auth_url(client_id, redirect_uri, st.session_state["oauth_state"])
            st.link_button("Continue with Google", auth_url, width="stretch")
            st.divider()
        else:
            st.info("Google login is available after adding GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env.")

        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", width="stretch"):
            user, token, message = authenticate_user(email, password)
            if user:
                st.session_state["user"] = user
                st.session_state["token"] = token
                st.success(message)
                st.rerun()
            else:
                st.error(message)
    else:
        st.subheader("Register")
        username = st.text_input("Username", key="register_username")
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Password", type="password", key="register_password")
        if st.button("Create Account", width="stretch"):
            ok, message = register_user(username, email, password)
            if ok:
                st.success(message)
            else:
                st.error(message)


def render_app_sidebar():
    with st.sidebar:
        st.header("Account")
        st.success(f"Logged in as {st.session_state['user']['username']}")
        if st.button("Logout"):
            st.session_state["user"] = None
            st.session_state["token"] = None
            st.rerun()

        st.header("Navigation")
        return st.radio(
            "Page",
            [
                "Dashboard",
                "Add Expense",
                "Budget Management",
                "Analysis",
                "Prediction",
                "Email Alerts",
                "Expense History",
            ],
            label_visibility="collapsed",
        )


def render_header(db_ready):
    st.title("Financial Expense Tracking & Analysis System")
    st.caption(
        "Track expenses, analyze spending behavior, predict future costs, and receive automatic overspending alerts."
    )
    if db_ready:
        st.success("Connected to MySQL database.")
    else:
        st.warning("Using sample dataset because MySQL is not connected.")


def render_summary(df):
    summary = calculate_summary(df)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Expenses", format_money(summary["total"]))
    col2.metric("Average Expense", format_money(summary["average"]))
    col3.metric("Highest Category", summary["highest_category"])
    col4.metric("Monthly Change", format_money(summary["change"]))


def run_login_alert_check(db_ready, df):
    if not db_ready or not st.session_state.get("user"):
        return

    user = st.session_state["user"]
    login_key = f"login_alert_checked_{user['id']}"
    if st.session_state.get(login_key):
        return

    st.session_state[login_key] = True
    try:
        status, message = send_automatic_alert_for_user(user, df)
        if status == "sent":
            st.success(message)
        elif status == "already_sent":
            st.info(message)
        elif status == "missing_config":
            st.info("Automatic alert detected overspending, but SMTP is not configured.")
        elif status == "failed":
            st.error(message)
    except Exception as exc:
        st.warning(f"Automatic email alert could not be sent: {exc}")


def render_add_expense(db_ready):
    st.subheader("Add Expense")
    with st.form("expense_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        amount = col1.number_input("Amount", min_value=1.0, step=50.0)
        category = col2.selectbox("Category", CATEGORIES)
        payment_mode = col3.selectbox("Payment Mode", PAYMENT_MODES)
        description = st.text_input("Description")
        expense_date = st.date_input("Expense Date", value=date.today())
        submitted = st.form_submit_button("Add Expense", width="stretch")

    if not submitted:
        return

    user = st.session_state.get("user") or {"id": 1}
    if db_ready and st.session_state.get("user"):
        save_expense(user["id"], amount, category, description, expense_date, payment_mode)
        latest_df = prepare_expense_frame(fetch_expenses(user["id"]))
        status, message = send_automatic_alert_for_user(user, latest_df)
        if status == "sent":
            st.success(message)
        elif status == "missing_config":
            st.warning("Expense added, but SMTP is not configured for automatic email alerts.")
        elif status == "failed":
            st.warning(message)
    else:
        st.session_state["demo_expenses"].append(
            {
                "Expense_ID": f"D{len(st.session_state['demo_expenses']) + 1}",
                "User_ID": user["id"],
                "Amount": amount,
                "Category": category,
                "Description": description,
                "Date": expense_date,
                "Payment_Mode": payment_mode,
            }
        )
    st.success("Expense added successfully.")


def render_budget_management(db_ready, df):
    st.subheader("Budget Management")

    if not db_ready:
        st.warning("Budget management requires MySQL connection.")
        return

    user = st.session_state["user"]
    today = date.today()
    selected_month = st.date_input(
        "Budget Month",
        value=date(today.year, today.month, 1),
        help="Select any date in the month. The budget is saved for that month.",
    )
    month_start = date(selected_month.year, selected_month.month, 1)
    month_label = month_start.strftime("%Y-%m")

    current_budget = fetch_budget(user["id"], month_start)
    current_budget_amount = float(current_budget["monthly_budget"]) if current_budget else 0.0

    with st.form("budget_form"):
        monthly_budget = st.number_input(
            "Monthly Budget",
            min_value=0.0,
            step=500.0,
            value=current_budget_amount,
        )
        submitted = st.form_submit_button("Save Budget", width="stretch")

    if submitted:
        upsert_budget(user["id"], monthly_budget, month_start)
        st.success(f"Budget saved for {month_label}.")
        current_budget_amount = monthly_budget

    prepared = prepare_expense_frame(df)
    if prepared.empty:
        month_spent = 0.0
    else:
        month_spent = float(prepared.loc[prepared["Month"] == month_label, "Amount"].sum())

    remaining = current_budget_amount - month_spent
    usage = (month_spent / current_budget_amount) if current_budget_amount else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Monthly Budget", format_money(current_budget_amount))
    col2.metric("Spent This Month", format_money(month_spent))
    col3.metric("Remaining", format_money(remaining))

    if current_budget_amount <= 0:
        st.info("Set a monthly budget to start tracking budget usage.")
    else:
        st.progress(min(usage, 1.0))
        usage_percent = usage * 100
        if usage >= 1:
            st.error(f"Budget exceeded. You have used {usage_percent:.1f}% of your monthly budget.")
        elif usage >= 0.8:
            st.warning(f"Budget warning. You have used {usage_percent:.1f}% of your monthly budget.")
        else:
            st.success(f"Budget is under control. You have used {usage_percent:.1f}% of your monthly budget.")

    st.subheader("Budget History")
    budgets = fetch_budgets(user["id"])
    if budgets.empty:
        st.info("No budgets saved yet.")
    else:
        st.dataframe(budgets, width="stretch")


def render_charts(df):
    if df.empty:
        st.info("No expense data available yet.")
        return

    left, right = st.columns(2)
    left.plotly_chart(category_pie_chart(df), width="stretch")
    right.plotly_chart(category_bar_chart(df), width="stretch")
    st.plotly_chart(monthly_line_chart(df), width="stretch")
    st.plotly_chart(daily_trend_chart(df), width="stretch")


def render_prediction(df):
    st.subheader("Machine Learning Prediction")
    prediction, monthly = predict_next_month_expense(df)

    if prediction is None:
        st.info("At least two months of data are required for prediction.")
        return

    st.metric("Predicted Next Month Expense", format_money(prediction))
    chart_data = monthly.copy()
    chart_data["Type"] = "Actual"
    forecast_month = f"Next Month"
    forecast = pd.DataFrame([{"Month": forecast_month, "Amount": prediction, "Type": "Predicted"}])
    st.plotly_chart(
        px.bar(pd.concat([chart_data[["Month", "Amount", "Type"]], forecast]), x="Month", y="Amount", color="Type"),
        width="stretch",
    )


def send_automatic_alert_for_user(user, df):
    increased, summary = expense_increased(df)
    if not increased:
        return "clear", "Expenses are under control. No alert email is required."

    sender_email, app_password = get_smtp_config()
    resend_api_key, resend_from_email = get_resend_config()
    if not resend_api_key and (not sender_email or not app_password):
        return "missing_config", "Email credentials are not configured."

    current_month = monthly_expenses(df).iloc[-1]["Month"]
    if alert_already_sent(user["id"], current_month):
        return "already_sent", "Alert email was already sent for this monthly comparison."

    body = build_alert_message(
        user["username"],
        summary["previous_month"],
        summary["current_month"],
    )
    try:
        send_alert_email(
            sender_email,
            app_password,
            user["email"],
            "Expense Alert Notification",
            body,
            resend_api_key,
            resend_from_email,
        )
    except EmailDeliveryError as exc:
        return "failed", f"Automatic email alert failed: {exc}"
    except OSError as exc:
        return (
            "failed",
            "Automatic email alert failed because the server could not reach Gmail SMTP "
            f"(smtp.gmail.com:587). Details: {exc}",
        )
    except Exception as exc:
        return "failed", f"Automatic email alert failed: {exc}"

    record_alert_sent(
        user["id"],
        current_month,
        summary["previous_month"],
        summary["current_month"],
    )
    return "sent", f"Alert email sent automatically to {user['email']}."


def send_automatic_alerts_to_all_users():
    sender_email, app_password = get_smtp_config()
    resend_api_key, resend_from_email = get_resend_config()
    if not resend_api_key and (not sender_email or not app_password):
        return [], ["Email credentials are not configured."]

    sent = []
    skipped = []
    for user in fetch_users():
        user_df = prepare_expense_frame(fetch_expenses(user["id"]))
        increased, summary = expense_increased(user_df)
        if not increased:
            skipped.append(f"{user['email']}: expenses are under control")
            continue

        body = build_alert_message(
            user["username"],
            summary["previous_month"],
            summary["current_month"],
        )
        try:
            send_alert_email(
                sender_email,
                app_password,
                user["email"],
                "Expense Alert Notification",
                body,
                resend_api_key,
                resend_from_email,
            )
            sent.append(user["email"])
        except Exception as exc:
            skipped.append(f"{user['email']}: email failed - {exc}")

    return sent, skipped


def render_alerts(df):
    st.subheader("Automatic Email Alert")
    increased, summary = expense_increased(df)
    previous_month = summary["previous_month"]
    current_month = summary["current_month"]

    col1, col2 = st.columns(2)
    col1.metric("Previous Month", format_money(previous_month))
    col2.metric("Current Month", format_money(current_month))

    if increased:
        st.error("Current month expenses increased compared to the previous month.")
    else:
        st.success("Expenses are under control based on the latest monthly comparison.")

    sender_email, app_password = get_smtp_config()
    resend_api_key, resend_from_email = get_resend_config()
    if resend_api_key:
        st.info("Resend email API is configured. Alerts will be sent automatically when spending increases.")
    elif sender_email and app_password:
        st.info("SMTP is configured. Alerts will be sent automatically when spending increases.")
    else:
        st.warning("Email is not configured. Set RESEND_API_KEY and RESEND_FROM_EMAIL, or set SMTP_EMAIL and SMTP_APP_PASSWORD.")

    user = st.session_state.get("user")
    if not user:
        return

    st.caption(f"Alert receiver email: {user['email']}")

    if not increased:
        return

    try:
        status, message = send_automatic_alert_for_user(user, df)
        if status == "sent":
            st.success(message)
        elif status == "already_sent":
            st.info(message)
        elif status == "missing_config":
            st.warning(message)
        elif status == "failed":
            st.error(message)
        else:
            st.info(message)
    except Exception as exc:
        st.error(f"Automatic email alert failed: {exc}")



def main():
    init_session()
    db_ready = mysql_available()
    if db_ready:
        initialize_database()

    if not st.session_state["user"]:
        render_auth_pages(db_ready)
        return

    page = render_app_sidebar()
    render_header(db_ready)

    df = get_expense_data(db_ready)
    render_summary(df)
    run_login_alert_check(db_ready, df)

    if page == "Dashboard":
        render_charts(df)
    elif page == "Add Expense":
        render_add_expense(db_ready)
    elif page == "Budget Management":
        render_budget_management(db_ready, df)
    elif page == "Analysis":
        st.subheader("Monthly Expense Analysis")
        st.dataframe(monthly_expenses(df), width="stretch")
        st.subheader("Category Expense Analysis")
        st.dataframe(category_expenses(df), width="stretch")
    elif page == "Prediction":
        render_prediction(df)
    elif page == "Email Alerts":
        render_alerts(df)
    else:
        st.subheader("Expense History")
        st.dataframe(df.sort_values("Date", ascending=False), width="stretch")


if __name__ == "__main__":
    main()
