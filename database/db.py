import os
from contextlib import contextmanager
from urllib.parse import unquote, urlparse

import mysql.connector
import pandas as pd
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# =========================
# DATABASE CONFIGURATION
# =========================


def get_env_value(*names, default=""):
    for name in names:
        value = os.getenv(name)
        if value:
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            return str(value).strip()
    return default


def build_db_config():
    mysql_url = get_env_value("MYSQL_PUBLIC_URL", "MYSQL_URL", "DATABASE_URL")

    if mysql_url:
        parsed_url = urlparse(mysql_url)
        database_name = unquote((parsed_url.path or "").lstrip("/"))

        return {
            "host": parsed_url.hostname,
            "user": unquote(parsed_url.username or ""),
            "password": unquote(parsed_url.password or ""),
            "database": database_name or get_env_value("MYSQLDATABASE", "MYSQL_DATABASE", default="expense_tracker"),
            "port": parsed_url.port or int(get_env_value("MYSQLPORT", "MYSQL_PORT", default="3306")),
        }

    return {
        "host": get_env_value("MYSQLHOST", "MYSQL_HOST", default="localhost"),
        "user": get_env_value("MYSQLUSER", "MYSQL_USER", default="root"),
        "password": get_env_value("MYSQLPASSWORD", "MYSQL_PASSWORD", default=""),
        "database": get_env_value("MYSQLDATABASE", "MYSQL_DATABASE", default="expense_tracker"),
        "port": int(get_env_value("MYSQLPORT", "MYSQL_PORT", default="3306")),
    }


DB_CONFIG = build_db_config()


# =========================
# MYSQL CONNECTION
# =========================

def get_connection():

    return mysql.connector.connect(**DB_CONFIG)


# =========================
# MYSQL CURSOR MANAGER
# =========================

@contextmanager
def mysql_cursor(dictionary=False):

    connection = get_connection()

    cursor = connection.cursor(dictionary=dictionary, buffered=True)

    try:
        yield cursor

        connection.commit()

    finally:
        cursor.close()

        connection.close()


# =========================
# MYSQL AVAILABILITY
# =========================

def mysql_available():

    try:

        with get_connection() as connection:

            return connection.is_connected()

    except mysql.connector.Error as e:

        print("MySQL Connection Error:", e)

        return False


# =========================
# INITIALIZE DATABASE
# =========================

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

                alert_type VARCHAR(20) DEFAULT 'increase',

                previous_amount DECIMAL(10,2) NOT NULL,

                current_amount DECIMAL(10,2) NOT NULL,

                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE KEY unique_user_alert_month_type(user_id, alert_month, alert_type),

                FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
            )
            """
        )

        ensure_email_alert_schema(cursor)


def ensure_email_alert_schema(cursor):

    cursor.execute("SHOW COLUMNS FROM email_alerts LIKE 'alert_type'")
    alert_type_columns = cursor.fetchall()
    if not alert_type_columns:
        cursor.execute(
            """
            ALTER TABLE email_alerts
            ADD COLUMN alert_type VARCHAR(20) DEFAULT 'increase'
            AFTER alert_month
            """
        )

    cursor.execute("SHOW INDEX FROM email_alerts WHERE Key_name = 'unique_user_alert_month'")
    old_unique_indexes = cursor.fetchall()
    if old_unique_indexes:
        cursor.execute("ALTER TABLE email_alerts DROP INDEX unique_user_alert_month")

    cursor.execute("SHOW INDEX FROM email_alerts WHERE Key_name = 'unique_user_alert_month_type'")
    new_unique_indexes = cursor.fetchall()
    if not new_unique_indexes:
        cursor.execute(
            """
            ALTER TABLE email_alerts
            ADD UNIQUE KEY unique_user_alert_month_type(user_id, alert_month, alert_type)
            """
        )


# =========================
# USER FUNCTIONS
# =========================

def find_user_by_email(email):

    with mysql_cursor(dictionary=True) as cursor:

        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )

        return cursor.fetchone()


def find_user_by_google_sub(google_sub):

    with mysql_cursor(dictionary=True) as cursor:

        cursor.execute(
            "SELECT * FROM users WHERE google_sub = %s",
            (google_sub,)
        )

        return cursor.fetchone()


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


# =========================
# ALERT FUNCTIONS
# =========================

def alert_already_sent(user_id, alert_month, alert_type):

    with mysql_cursor(dictionary=True) as cursor:

        cursor.execute(
            """
            SELECT id

            FROM email_alerts

            WHERE user_id = %s
            AND alert_month = %s
            AND alert_type = %s
            """,
            (user_id, alert_month, alert_type),
        )

        return cursor.fetchone() is not None


def record_alert_sent(
    user_id,
    alert_month,
    alert_type,
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
                alert_type,
                previous_amount,
                current_amount
            )

            VALUES(%s, %s, %s, %s, %s)
            """,
            (
                user_id,
                alert_month,
                alert_type,
                previous_amount,
                current_amount,
            ),
        )


# =========================
# USER CREATION
# =========================

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


# =========================
# EXPENSE FUNCTIONS
# =========================

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

        rows = cursor.fetchall()
        columns = [
            "Expense_ID",
            "User_ID",
            "Amount",
            "Category",
            "Description",
            "Date",
            "Payment_Mode",
        ]
        return pd.DataFrame(rows, columns=columns)


# =========================
# BUDGET FUNCTIONS
# =========================

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
