# Financial Expense Tracking & Analysis System

A smart Streamlit web application for tracking expenses, analyzing spending behavior, managing monthly budgets, predicting future expenses with Machine Learning, and sending automatic overspending email alerts.

The app is designed as a single Streamlit project: the UI, backend logic, database access, ML prediction, and email alert automation run together from `app.py`.

## Live Deployment

The project has been deployed on Railway.

Live app:

```text
https://financial-expense-tracking-analysis-system-production.up.railway.app
```

Based on the latest deployment screenshots, the app is live and the page is loading successfully with:

```text
Connected to MySQL database.
```

Current deployment status:

| Feature | Status |
| --- | --- |
| Streamlit app on Railway | Working |
| Railway MySQL connection | Working |
| Login/Register | Working |
| Google OAuth | Added, requires correct Google redirect URI |
| Expense tracking | Working |
| Budget management | Working |
| Dashboard/Analysis/Prediction | Working |
| Email alerts | Implemented; Railway should use Resend API instead of Gmail SMTP |

Note: Gmail SMTP worked locally, but Railway had network issues reaching Gmail SMTP. The project now supports **Resend API** for deployed email alerts.

## Main Features

- User registration and login
- Password hashing with bcrypt
- JWT session token generation
- Google OAuth login support
- Add and view expenses
- Category and payment mode tracking
- MySQL database storage
- Dashboard charts and spending summaries
- Monthly/category expense analysis
- Budget management by month
- Linear Regression expense prediction
- Automatic email alerts when current month spending is greater than previous month spending
- CSV fallback dataset for demo mode when MySQL is unavailable

## Tech Stack

| Category | Technology |
| --- | --- |
| Web App | Streamlit |
| Backend Logic | Python |
| Database | MySQL |
| Database Driver | mysql-connector-python |
| Data Analysis | Pandas, NumPy |
| Visualization | Plotly |
| Machine Learning | Scikit-learn Linear Regression |
| Password Security | bcrypt |
| Authentication Token | PyJWT |
| Google Login | Google OAuth 2.0, requests |
| Local Email Sending | Gmail SMTP / smtplib |
| Deployed Email Sending | Resend Email API |
| Environment Config | `.env`, Railway Variables |
| Deployment | Railway |

## Project Structure

```text
Financial_Expense_Tracker/
|-- app.py
|-- Procfile
|-- README.md
|-- requirements.txt
|-- expenses_dataset.csv
|
|-- auth/
|   |-- google_oauth.py
|   |-- login.py
|   |-- register.py
|   `-- __init__.py
|
|-- database/
|   |-- db.py
|   `-- __init__.py
|
|-- modules/
|   |-- add_expense.py
|   |-- analysis.py
|   |-- email_alert.py
|   |-- prediction.py
|   |-- visualization.py
|   `-- __init__.py
|
`-- docs/
    `-- screenshots/
        |-- login.png
        |-- register.png
        |-- dashboard.png
        |-- dashboard_1.png
        |-- add-expense.png
        |-- budget-management.png
        |-- analysis.png
        |-- prediction.png
        |-- email-alerts.png
        `-- expense-history.png
```

## How the App Works

```text
Register/Login
      |
JWT Session
      |
Add Expenses
      |
Store in MySQL
      |
Analyze and Visualize Spending
      |
Predict Next Month Expense
      |
Compare Current Month vs Previous Month
      |
Send Automatic Email Alert if Spending Increased
```

## Local Setup

Open the project folder:

```cmd
cd "C:\Users\sai jaswanth\Desktop\Financial_Expense_Tracker"
```

Create and activate a virtual environment:

```cmd
python -m venv venv
venv\Scripts\activate
```

Install dependencies:

```cmd
pip install -r requirements.txt
```

Create a local MySQL database:

```sql
CREATE DATABASE expense_tracker;
```

Run the app:

```cmd
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

## Environment Variables

Create a `.env` file for local development. Do not commit this file.

### Local MySQL

```env
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=expense_tracker
MYSQL_PORT=3306
```

The app also supports Railway-style variable names:

```env
MYSQLHOST=your_host
MYSQLUSER=your_user
MYSQLPASSWORD=your_password
MYSQLDATABASE=your_database
MYSQLPORT=3306
```

It also supports MySQL connection URLs:

```env
MYSQL_PUBLIC_URL=mysql://user:password@host:port/database
MYSQL_URL=mysql://user:password@host:port/database
DATABASE_URL=mysql://user:password@host:port/database
```

### JWT

```env
JWT_SECRET_KEY=use_a_long_secure_secret_key_at_least_32_characters
```

### Google OAuth

```env
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8501
```

For Railway deployment, use the deployed app URL:

```env
GOOGLE_REDIRECT_URI=https://financial-expense-tracking-analysis-system-production.up.railway.app
```

The same redirect URI must also be added in Google Cloud Console under OAuth authorized redirect URIs.

### Email Alerts

The project supports two email methods.

For local Gmail SMTP testing:

```env
SMTP_EMAIL=your_sender_gmail@gmail.com
SMTP_APP_PASSWORD=your_gmail_app_password
```

For Railway deployment, use Resend:

```env
RESEND_API_KEY=your_resend_api_key
RESEND_FROM_EMAIL=Financial Expense Tracker <onboarding@resend.dev>
```

Important:

- Gmail SMTP may work locally but can fail on Railway because outbound SMTP can be blocked or unreachable.
- Resend uses HTTPS and is better for Railway deployment.
- With Resend test mode, `onboarding@resend.dev` may only send to the email address used for the Resend account.
- To send alerts to any registered user email, verify a domain in Resend and use a sender like `alerts@yourdomain.com`.

## Railway Deployment

The project includes a `Procfile`:

```text
web: streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

Railway setup:

1. Create a Railway project.
2. Add a Web Service from the GitHub repository.
3. Add a MySQL service.
4. Add required variables to the Web Service.
5. Deploy.

Recommended Railway Web Service variables:

```env
MYSQL_PUBLIC_URL=your_railway_mysql_public_url
JWT_SECRET_KEY=use_a_long_secure_secret_key_at_least_32_characters
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://financial-expense-tracking-analysis-system-production.up.railway.app
RESEND_API_KEY=your_resend_api_key
RESEND_FROM_EMAIL=Financial Expense Tracker <onboarding@resend.dev>
```

Optional local SMTP variables can also be kept, but Resend is preferred for Railway:

```env
SMTP_EMAIL=your_sender_gmail@gmail.com
SMTP_APP_PASSWORD=your_gmail_app_password
```

## Dataset Usage

The project includes a custom dataset:

```text
expenses_dataset.csv
```

The dataset is used as sample/demo data when MySQL is not connected. When MySQL is connected and a user is logged in, the app uses that user's real expense records from the database.

Dataset columns include:

| Column | Description |
| --- | --- |
| Expense_ID | Sample expense ID |
| Date | Expense date |
| Category | Spending category |
| Amount | Expense amount |
| Payment_Mode | Payment method |
| Description | Expense note |
| Monthly_Budget | Sample budget value |
| Savings | Sample savings value |
| Expense_Status | Sample budget/spending status |

Data source behavior:

| Condition | Data Source |
| --- | --- |
| MySQL connected and user logged in | MySQL user expense records |
| MySQL not connected | `expenses_dataset.csv` |

## Application Pages

### Login

Users can log in with email/password or continue with Google OAuth.

![Login Page](docs/screenshots/login.png)

### Register

New users can create an account using username, email, and password.

![Register Page](docs/screenshots/register.png)

### Dashboard

Shows total expenses, average expense, highest category, monthly change, and visual charts.

![Dashboard](docs/screenshots/dashboard.png)
![Dashboard](docs/screenshots/dashboard_1.png)

### Add Expense

Allows users to add amount, category, payment mode, description, and expense date. After adding an expense, the automatic email alert check runs in the backend.

![Add Expense Page](docs/screenshots/add-expense.png)

### Budget Management

Allows users to set a monthly budget, view spending for that month, see remaining budget, and track budget usage.

![Budget Management Page](docs/screenshots/budget-management.png)

### Analysis

Shows monthly expense totals and category-wise expense totals.

![Analysis Page](docs/screenshots/analysis.png)

### Prediction

Uses Linear Regression to predict the next month expense from monthly spending history.

![Prediction Page](docs/screenshots/prediction.png)

### Email Alerts

Compares previous month and current month expenses. If current month spending is higher, an alert email is sent automatically.

![Email Alerts Page](docs/screenshots/email-alerts.png)

### Expense History

Displays saved expenses for the logged-in user.

![Expense History Page](docs/screenshots/expense-history.png)

## Automatic Email Alert System

Email alert logic:

```text
Current Month Expense > Previous Month Expense
        |
Send Email Alert
        |
Record Alert in email_alerts table
```

Alerts run automatically:

- after login
- after adding a new expense
- when opening the Email Alerts page

The app avoids duplicate alerts using the `email_alerts` table. One alert is recorded per user per alert month.

If the app shows a Resend `403 Forbidden` error, check:

- `RESEND_API_KEY` is correct.
- `RESEND_FROM_EMAIL` is allowed by Resend.
- The receiver email is allowed in Resend test mode.
- A real sending domain is verified if sending to any user email.

## Machine Learning Prediction

The prediction module groups expenses by month and trains a Linear Regression model.

Requirements:

- At least two months of expense data
- Monthly expense totals

Output:

```text
Predicted Next Month Expense
```

## Database Tables

The app automatically creates these tables:

### users

| Column | Purpose |
| --- | --- |
| id | User ID |
| username | User name |
| email | Unique email |
| password | Hashed password, nullable for Google users |
| auth_provider | `local` or `google` |
| google_sub | Google OAuth subject ID |
| created_at | Account timestamp |

### expenses

| Column | Purpose |
| --- | --- |
| id | Expense ID |
| user_id | Owner user ID |
| amount | Expense amount |
| category | Expense category |
| description | Expense note |
| expense_date | Expense date |
| payment_mode | Payment method |
| created_at | Record timestamp |

### budgets

| Column | Purpose |
| --- | --- |
| id | Budget ID |
| user_id | Owner user ID |
| monthly_budget | Budget amount |
| month_start | First date of the budget month |

### email_alerts

| Column | Purpose |
| --- | --- |
| id | Alert ID |
| user_id | User who received the alert |
| alert_month | Month for the alert |
| previous_amount | Previous month expense |
| current_amount | Current month expense |
| sent_at | Alert timestamp |

## Verification Checklist

Run syntax check:

```cmd
py -m compileall app.py auth database modules
```

Run locally:

```cmd
streamlit run app.py
```

Functional checks:

1. Register a new user.
2. Log in with email/password.
3. Try Google OAuth login.
4. Add previous month expense records.
5. Add current month expense records.
6. Confirm dashboard values update.
7. Set a monthly budget.
8. Check analysis tables.
9. Check prediction page with at least two months of data.
10. Confirm Email Alerts page compares previous/current month.
11. Confirm Resend is configured on Railway for deployed email alerts.
12. Check `email_alerts` table after a successful sent alert.

## Important Notes

- Do not commit `.env` or any secret keys.
- Rotate credentials if they were shared publicly.
- The app is live on Railway when the deployed URL opens and shows `Connected to MySQL database`.
- Email alerts on Railway should use Resend API, not Gmail SMTP.
- Gmail SMTP can still be used for local testing.
