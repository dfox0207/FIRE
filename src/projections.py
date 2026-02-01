import pandas as pd
from pathlib import Path
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from dataclasses import dataclass
from typing import Dict, Optional, List


"""
Takes nominal net worth calculated from Balances.csv and plots it. 

"""

DRIVE_BASE = Path("/content/drive/MyDrive/Finances/FIRE")

BALANCES_CSV = DRIVE_BASE / "Balances.csv"
CASHFLOW_CSV = DRIVE_BASE / "cashflow_schedule.csv"

#Assumptions
# Global nominal annual return assumption (you can later replace with per-account returns)
DEFAULT_ANNUAL_RETURN = 0.07 

# Projection horizon:
# - If there are any open-ended (blank end_date) rows in cashflow_schedule.csv,
#   we'll project this many years past the latest actual date by default.  
OPEN_ENDED_YEARS = 30

# If you'd rather hard-set an end date, set this to "YYYY-MM-DD" (or None to auto)
PROJECTION_END_DATE: Optional[str] = None



def net_worth():
    #read BALANCES.CSV
    df = pd.read_csv(BALANCES_CSV, parse_dates=["Date"])            #changed csv_path to BALANCES_CSV

    #identify balance columns (everything except date)
    balance_cols = [c for c in df.columns if c != "Date"]

    #compute net worth per row
    df["net_worth"] = df[balance_cols].sum(axis=1)

    #plot Net Worth Actuals
    df['Date'] = pd.to_datetime(df['Date'])
    plt.plot(df['Date'],df['net_worth'], marker='o', linestyle='-', color='b')
    plt.title('Net Worth')
    plt.xlabel('Date')
    plt.ylabel('Net Worth ($)')
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def _to_month_start(dt: pd.Timestamp) -> pd.Timestamp:
    """Normalize a timestamp to the first day of that month."""

    dt = pd.Timestamp(dt)
    return pd.Timestamp(year=dt.year, month=dt.month, day=1)

def load_latest_actual_balances(balances_path: Path) -> tuple[pd.Timestamp, Dict[str, float]]:
    """
    Loads Balances.csv and returns:
    - latest Date (as month-start)
    - dict: (account_name: latest_balance)
    """
    df = pd.read_csv(balances_path)
    if "Date" not in df.columns:
        raise ValueError(f"'Date' column not found in (balances_path). Found columns: {list(df.columns)}")

    df["Date"]= pd.to_datetime(df["Date"], errors="coerce")    
    df = df.dropna(subset=["Date"]).sort_values("Date")
    if df.empty:
        raise ValueError(f"No valid dates found in {balances_path}.")
    
    latest_row = df.iloc[-1]
    latest_date = _to_month_start(latest_row["Date"])

    #All non-Date columns are treated as accounts
    acct_cols = [c for c in df.columns if c != "Date"]
    balances: Dict[str, float] = {}
    for c in acct_cols:
        val = latest_row[c]
        #Coerce to float, treat blanks as 0
        try:
            balances[c] = float(val) if pd.notna(val) else 0.0
        except Exception:
            #if column has currency strings like "$1,234", try cleaning
            cleaned = str(val).replace("$", "").replace(",", "").strip()
            balances[c] = float(cleaned) if cleaned else 0.0
    
    return latest_date, balances

def load_cashflow_schedule(schedule_path: Path) -> pd.DataFrame:
    """
    Loads cashflow_schedule.csv with expected columns:
        start_date, end_date, account, monthly_amount
    Returns cleaned DataFrame with parsed dates.
    """
    sched = pd.read_csv(schedule_path)

    required = {"start_date", "end_date", "account", "monthly_amount"}
    missing = required - set(sched.columns)
    if missing:
        raise ValueError(
            f"cashflow_schedule.csv is missing columns {sorted(missing)}. "
            f"Found columns: {list(sched.columns)}"
        )
    
    sched["start_date"] = pd.to_datetime(sched["start_date"], errors="coerce")
    #end_date may be blank; keep NaT as open-ended
    sched["end_date"] = pd.to_datetime(sched["end_date"], errors="coerce")

    sched = sched.dropna(subset=["start_date", "account", "monthly_amount"]).copy()
    sched["account"] = sched["account"].astype(str).str.strip()
    sched["monthly_amount"] = pd.to_numeric(sched["monthly_amount"], errors="coerce").fillna(0.0)

    # Normalize date ranges to month starts
    sched["start_date"] = sched["start_date"].map(_to_month_start)
    sched["end_date"] = sched["end_date"].map(lambda x: _to_month_start(x) if pd.notna(x) else pd.NaT)

    return sched




def determine_projection_end(
    latest_actual_month: pd.Timestamp,
    schedule: pd.DataFrame,
    explicit_end: Optional[str],
    open_ended_years: int,
    ) -> pd.Timestamp:
    if explicit_end:
        return _to_month_start(pd.to_datetime(explicit_end))
    
    has_open_ended = schedule["end_date"].isna().any()
    max_end = schedule["end_date"].dropna().max() if schedule["end_date"].notna().any() else pd.NaT

    if has_open_ended:
        return _to_month_start(latest_actual_month+pd.DateOffset(years=open_ended_years))
    if pd.notna(max_end):
        return _to_month_start(max_end)
    
def monthly_cashflows_for_month(schedule: pd.DataFrame, month: pd.Timestamp) -> pd.Series:
    """
    Returns a Series indexed by account with the total monthly_amount active for `month`.
    Active if:
      start_date <= month <= end_date  OR end_date is NaT (open-ended)
    """
    active = schedule[
        (schedule["start_date"] <= month) 
        & (schedule["end_date"].isna() | (schedule["end_date"] >= month))
    ]    
    if active.empty:
        return pd.Series(dtype=float)
    return active.groupby("account")["monthly_amount"].sum()


def project_balances(
    start_month: pd.Timestamp,
    start_balances: Dict[str, float],
    schedule: pd.DataFrame,
    end_month: pd.Timestamp,
    annual_return: float = DEFAULT_ANNUAL_RETURN
    ) -> pd.DataFrame:

    """
    Projects nominal balances monthly from the month AFTER start_month through end_month (inclusive).
    Applies growth first, then cashflows each month.
    """
    # Timeline starts next month (since start_month is the last actual)
    first_proj_month = _to_month_start(start_month + pd.DateOffset(months=1))
    months = pd.date_range(first_proj_month, end_month, freq="MS")
    if len(months) ==0:
        raise ValueError("Projection range is empty. Check your end date vs latest actual date.")

    accounts = sorted(set(start_balances.keys()) | set(schedule["accounts"].unique()))
    balances = pd.Series({a: float(start_balances.get(a, 0.0)) for a in accounts}, dtype=float)  

    monthly_r = (1.0 + annual_return) ** (1.0/12.0)  - 1.0

    rows: List[dict] = []
    for m in months:
        #growth
        balances = balances*1.0




def main():                     #this is the main function that runs the other helper functions
    net_worth()

    # test_month, latest_balances = load_latest_actual_balances(BALANCES_CSV)
    # schedule = load_cashflow_schedule(CASHFLOW_CSV)

    # end_month = determine_projection_end(
    #     latest_actual_month=latest_month,
    #     schedule=schedule,
    #     explicit_end=PROJECTION_laEND_DATE,
    #     open_ended_years=OPEN_ENDED_YEARS,
    # )

    # projection_df = project_balances(
    #     start_month=latest_month,
    #     start_balances=latest_balances,
    #     schedule=schedule,
    #     end_month=end_month,
    #     annual_return=DEFAULT_ANNUAL_RETURN,
    # )    

if __name__ == "__main__":
    main()