import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from modules.analysis import calculate_summary


def build_alert_message(username, previous_month, current_month):
    increase = current_month - previous_month
    return f"""Hello {username},

Your current month expense has increased compared to the previous month.

Previous Month Expense: Rs. {previous_month:.2f}
Current Month Expense: Rs. {current_month:.2f}
Increase Amount: Rs. {increase:.2f}

Please reduce unnecessary spending and manage your expenses carefully.

Financial Expense Tracking System
"""


def expense_increased(df):
    summary = calculate_summary(df)
    return summary["current_month"] > summary["previous_month"] > 0, summary


def send_alert_email(sender_email, app_password, receiver_email, subject, body):
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(message)
