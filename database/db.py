import os
from contextlib import contextmanager

import mysql.connector
import pandas as pd
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("MYSQLHOST", "localhost"),
    "user": os.getenv("MYSQLUSER", "root"),
    "password": os.getenv("MYSQLPASSWORD", ""),
    "database": os.getenv("MYSQLDATABASE", "expense_tracker"),
    "port": int(os.getenv("MYSQLPORT", 3306)),
}


# Create MySQL Connection
def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


# Context Manager for Cursor Handling
@contextmanager
def mysql_cursor(dictionary=False):

    connection = get_connection()

    cursor = connection.cursor(dictionary=dictionary)

    try:
        yield cursor

        connection.commit()

    finally:
        cursor.close()

        connection.close()


# Check MySQL Availability
def mysql_available():

    try:
        with get_connection() as connection:
            return connection.is_connected()

    except mysql.connector.Error:
        return False


# Initialize Database Tables
def initialize_database():

    with mysql_cursor() as cursor:

        # USERS TABLE
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (

                id INT AUTO_INCREMENT PRIMARY KEY,

                username VARCHAR(100) NOT NULL,

                email VARCHAR(255) NOT NULL UNIQUE,

                password VARCHAR(255),

                auth_provider VARCHAR(50) DEFAULT 'local',

                google_sub VARCHAR(255) UNIQUE,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # EXPENSES TABLE
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (

                id INT AUTO_INCREMENT PRIMARY KEY,

                user_id INT NOT NULL,

                amount DECIMAL(10,2) NOT NULL,

                category VARCHAR(100) NOT NULL,

                description VARCHAR(255),

                expense_date DATE NOT NULL,

                payment_mode VARCHAR(50) DEFAULT 'UPI',

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
            )
            """
        )

        # BUDGETS TABLE
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS budgets (

                id INT AUTO_INCREMENT PRIMARY KEY,

                user_id INT NOT NULL,

                monthly_budget DECIMAL(10,2) NOT NULL,

                month_start DATE NOT NULL,

                UNIQUE KEY unique_user_month(user_id, month_start),

                FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
            )
            """
        )

        # EMAIL ALERTS TABLE
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS email_alerts (

                id INT AUTO_INCREMENT PRIMARY KEY,

                user_id INT NOT NULL,

                alert_month VARCHAR(7) NOT NULL,

                previous_amount DECIMAL(10,2) NOT NULL,

                current_amount DECIMAL(10,2) NOT NULL,

                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE KEY unique_user_alert_month(user_id, alert_month),

                FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
            )
            """
        )


# Find User By Email
def find_user_by_email(email):

    with mysql_cursor(dictionary=True) as cursor:

        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )

        return cursor.fetchone()


# Find User By Google Sub
def find_user_by_google_sub(google_sub):

    with mysql_cursor(dictionary=True) as cursor:

        cursor.execute(
            "SELECT * FROM users WHERE google_sub = %s",
            (google_sub,)
        )

        return cursor.fetchone()


# Fetch All Users
def fetch_users():

    with mysql_cursor(dictionary=True) as cursor:

        cursor.execute(
            """
            SELECT
                id,
                username,
                email

            FROM users

            ORDER BY username
            """
        )

        return cursor.fetchall()


# Check If Alert Already Sent
def alert_already_sent(user_id, alert_month):

    with mysql_cursor(dictionary=True) as cursor:

        cursor.execute(
            """
            SELECT id

            FROM email_alerts

            WHERE user_id = %s
            AND alert_month = %s
            """,
            (user_id, alert_month),
        )

        return cursor.fetchone() is not None


# Record Alert
def record_alert_sent(
    user_id,
    alert_month,
    previous_amount,
    current_amount
):

    with mysql_cursor() as cursor:

        cursor.execute(
            """
            INSERT IGNORE INTO email_alerts
            (
                user_id,
                alert_month,
                previous_amount,
                current_amount
            )

            VALUES(%s, %s, %s, %s)
            """,
            (
                user_id,
                alert_month,
                previous_amount,
                current_amount,
            ),
        )


# Create Local User
def create_user(username, email, hashed_password):

    with mysql_cursor() as cursor:

        cursor.execute(
            """
            INSERT INTO users
            (
                username,
                email,
                password,
                auth_provider
            )

            VALUES(%s, %s, %s, 'local')
            """,
            (
                username,
                email,
                hashed_password,
            ),
        )


# Create Google User
def create_google_user(username, email, google_sub):

    with mysql_cursor() as cursor:

        cursor.execute(
            """
            INSERT INTO users
            (
                username,
                email,
                password,
                auth_provider,
                google_sub
            )

            VALUES(%s, %s, NULL, 'google', %s)
            """,
            (
                username,
                email,
                google_sub,
            ),
        )


# Link Google Account
def link_google_to_existing_user(user_id, google_sub):

    with mysql_cursor() as cursor:

        cursor.execute(
            """
            UPDATE users

            SET google_sub = %s

            WHERE id = %s
            AND google_sub IS NULL
            """,
            (
                google_sub,
                user_id,
            ),
        )


# Add Expense
def add_expense(
    user_id,
    amount,
    category,
    description,
    expense_date,
    payment_mode
):

    with mysql_cursor() as cursor:

        cursor.execute(
            """
            INSERT INTO expenses
            (
                user_id,
                amount,
                category,
                description,
                expense_date,
                payment_mode
            )

            VALUES(%s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                amount,
                category,
                description,
                expense_date,
                payment_mode,
            ),
        )


# Insert Or Update Budget
def upsert_budget(
    user_id,
    monthly_budget,
    month_start
):

    with mysql_cursor() as cursor:

        cursor.execute(
            """
            INSERT INTO budgets
            (
                user_id,
                monthly_budget,
                month_start
            )

            VALUES(%s, %s, %s)

            ON DUPLICATE KEY UPDATE

            monthly_budget = VALUES(monthly_budget)
            """,
            (
                user_id,
                monthly_budget,
                month_start,
            ),
        )


# Fetch Budget
def fetch_budget(user_id, month_start):

    with mysql_cursor(dictionary=True) as cursor:

        cursor.execute(
            """
            SELECT *

            FROM budgets

            WHERE user_id = %s
            AND month_start = %s
            """,
            (
                user_id,
                month_start,
            ),
        )

        return cursor.fetchone()


# Fetch All Budgets
def fetch_budgets(user_id):

    with mysql_cursor(dictionary=True) as cursor:

        cursor.execute(
            """
            SELECT

                id AS Budget_ID,

                monthly_budget AS Monthly_Budget,

                month_start AS Month_Start

            FROM budgets

            WHERE user_id = %s

            ORDER BY month_start DESC
            """,
            (user_id,),
        )

        return pd.DataFrame(cursor.fetchall())


# Fetch Expenses
def fetch_expenses(user_id=None):

    query = """
        SELECT

            id AS Expense_ID,

            user_id AS User_ID,

            amount AS Amount,

            category AS Category,

            description AS Description,

            expense_date AS Date,

            payment_mode AS Payment_Mode

        FROM expenses
    """

    params = ()

    if user_id is not None:

        query += " WHERE user_id = %s"

        params = (user_id,)

    query += " ORDER BY expense_date DESC"

    with mysql_cursor(dictionary=True) as cursor:

        cursor.execute(query, params)

        return pd.DataFrame(cursor.fetchall())