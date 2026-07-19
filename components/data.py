from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def read_csv_safe(filename: str) -> pd.DataFrame:
    path = ROOT / filename
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def load_data():
    radar = read_csv_safe("radar_results.csv")
    history = read_csv_safe("history.csv")
    results = read_csv_safe("results.csv")
    return radar, history, results

def grade_results(results_df: pd.DataFrame) -> pd.DataFrame:
    if results_df.empty:
        return results_df

    required = {"actual_pra", "prediction", "book_line"}
    if not required.issubset(results_df.columns):
        return results_df

    results_df = results_df.copy()

    def result_for(row):
        if pd.isna(row.get("actual_pra")):
            return ""
        actual = float(row["actual_pra"])
        line = float(row["book_line"])
        prediction = str(row["prediction"]).upper()
        if prediction == "OVER":
            return "WIN" if actual > line else "LOSS"
        if prediction == "UNDER":
            return "WIN" if actual < line else "LOSS"
        return ""

    results_df["result"] = results_df.apply(result_for, axis=1)

    def profit_for(row):
        if row.get("result") == "WIN":
            return float(row.get("odds", 1.9)) - 1
        if row.get("result") == "LOSS":
            return -1.0
        return 0.0

    results_df["profit"] = results_df.apply(profit_for, axis=1)
    return results_df
