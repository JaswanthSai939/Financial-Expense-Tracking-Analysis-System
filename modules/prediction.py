import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from modules.analysis import monthly_expenses


def predict_next_month_expense(df):
    monthly = monthly_expenses(df)
    if len(monthly) < 2:
        return None, monthly

    monthly = monthly.copy()
    monthly["Index"] = np.arange(1, len(monthly) + 1)

    model = LinearRegression()
    model.fit(monthly[["Index"]], monthly["Amount"])

    next_index = pd.DataFrame({"Index": [len(monthly) + 1]})
    prediction = float(model.predict(next_index)[0])
    return max(prediction, 0), monthly
