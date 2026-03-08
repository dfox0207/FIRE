import json
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

from dataclasses import dataclass
from typing import Dict, Optional, List

from projection_engine import projection_engine



#read config file
#1. load config JSON
scenario_path = Path(sys.argv[1]) if len(sys.argv) >1 else Path("Config/base.json")
cfg = json.loads(scenario_path.read_text(encoding="utf-8"))

#2. Convert config values to proper Python types
assumptions = {
    "birthday": pd.Timestamp(cfg["birthday"]),
    "annual_return" : cfg["annual_return"],
    "inflation": cfg["inflation"],
    "horizon": pd.Timestamp(cfg["horizon"]).to_period("M").to_timestamp(),
    "basis": pd.Timestamp(cfg["basis"]),
    "withdrawal_start_date": pd.Timestamp(cfg["withdrawal_start_date"]),
    "withdrawal_rate": cfg["withdrawal_rate"],
    "withdrawal_type": cfg["withdrawal_type"],
    "withdrawal_order": cfg["withdrawal_order"],
    "pension": cfg["pension"],
    "service_length": cfg["service_length"],
    "mra": cfg["mra"],
    "high_3": cfg["high_3"],
    "ssa_benefit": cfg["ssa_benefit"]
}




#read Balances.csv
BALANCES_CSV = Path("/content/drive/MyDrive/Finances/FIRE/Balances.csv")
bal = pd.read_csv(BALANCES_CSV)
bal["Date"] = pd.to_datetime(bal["Date"])
bal = bal.sort_values("Date")              #sort on Date so last month's balances are the last row
latest = bal.iloc[-1] #take the last row (last month)
#select last months balances
start_month = latest["Date"].to_period("M").to_timestamp() + pd.DateOffset(months=1)  #start month is the last month plus 1.

bal = bal.set_index("Date")
                      


accounts = [c for c in bal.columns if c != "Date"]
start_bal = latest[accounts].fillna(0).astype(float)        #last month's balances


#read cashflow_schedule.csv
CASHFLOW_CSV = Path("/content/drive/MyDrive/Finances/FIRE/cashflow_schedule.csv")
cf = pd.read_csv(CASHFLOW_CSV)
cf["start_date"]= pd.to_datetime(cf["start_date"]).dt.to_period("M").dt.to_timestamp() + pd.DateOffset(months=1)     #convert start dates to beginning of next month
cf["end_date"]= pd.to_datetime(cf["end_date"], errors="coerce").dt.to_period("M").dt.to_timestamp()  #convert end dates to beginning of month, if no end date, convert to NaT
cf["monthly_amount"]= pd.to_numeric(cf["monthly_amount"]).fillna(0.0)
cf["account"]= cf["account"].astype(str).str.strip()                        #remove spaces before or after account names

if cf["end_date"].notna().any():
    last_sched_end = cf["end_date"].dropna().max()
else:
    last_sched_end = pd.NaT 

end_month= assumptions["horizon"]

months = pd.date_range(start_month, end_month, freq="MS")



def plot_networth(df, ax):
    
    #read BALANCES.CSV
    df_bal = pd.read_csv(BALANCES_CSV, parse_dates=["Date"])       

    #identify balance columns (everything except date)
    balance_cols = [c for c in df_bal.columns if c != "Date"]

    #compute net worth per row
    df_bal["net_worth"] = df_bal[balance_cols].sum(axis=1)

    #plot Net Worth Actuals
    df_bal['Date'] = pd.to_datetime(df_bal['Date'])
    ax.plot(df_bal['Date'],df_bal['net_worth'], label='Actual Balances', linestyle='-', color='b')

    #plot Prjected Net Worth Nominals
    df['Date'] = pd.to_datetime(df['Date'])
    ax.plot(df['Date'],df['Net_Worth'], label='Projected Nominal Balances', linestyle='dotted', color='r')

    #plot Prjected Net Worth Nominals
    df['Date'] = pd.to_datetime(df['Date'])
    ax.plot(df['Date'],df['Net_Worth_Real'], label='Projected Real Balances', linestyle='dotted', color='g')

    # Format Chart Title and Axises
    ax.set_title('Net Worth')
    ax.set_xlabel('Date')
    ax.set_ylabel('Net Worth ($)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"${v/1e6:.2f}M"))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True)
    ax.legend()

def plot_accounts(df, accounts, ax):              

    #plot Account Nominal Balances
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    for acct in accounts:
        ax.plot(df['Date'],df[acct], label=f"{acct} Balances")

    # Format Chart Title and Axises
    ax.set_title('Account Balances')
    ax.set_xlabel('Date')
    ax.set_ylabel('Balance ($)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"${v/1e6:.2f}M"))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True)
    ax.legend()

def plot_income(df, ax):

    #plot Projected Income
    df['Date'] = pd.to_datetime(df['Date'])
    ax.plot(df['Date'],df['Income_Real'], label='Real Income')
    ax.plot(df['Date'],df['Income'], label='Nominal Income')
    ax.plot(df['Date'],df['Net_Income_Real'], label='Net Real Income')
    
    # Format Chart Title and Axises
    ax.set_title('Income')
    ax.set_xlabel('Date')
    ax.set_ylabel('($)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"${v/1e3:.2f}k"))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True)
    ax.legend()
    
def plot_tax(df, ax):

    #plot Projected Income
    df['Date'] = pd.to_datetime(df['Date'])
    ax.plot(df['Date'],df['Total Tax'], label='Taxes')
    
    
    # Format Chart Title and Axises
    ax.set_title('Taxes- Real (2025)')
    ax.set_xlabel('Date')
    ax.set_ylabel('($)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"${v/1e3:.2f}k"))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True)
    ax.legend()

def main():

    projection = projection_engine(
        start_bal, 
        cf, 
        months, 
        assumptions,
        balances_actuals = bal
    )
    
    print(json.dumps(cfg, indent=2, sort_keys=True))

    # Create two side-by-side subplots
    fig, ax = plt.subplots(2, 2, figsize=(14, 8), sharex=True)

    # Top Left Plot: Networth
    plot_networth(projection, ax[0,0])
    

    # Top Right Plot: Income
    plot_income(projection, ax[0,1])

    # Bottom Left Plot: Account Balances
    plot_accounts(projection, assumptions["withdrawal_order"], ax[1,0])

    #Bottom Right Plot: Taxes
    plot_tax(projection, ax[1,1])

    plt.tight_layout()
    plt.show()

    scenario_path = Path(sys.argv[1]).resolve()

    # assuming config is in ClientFolder/Config/base.json
    client_root = scenario_path.parent.parent
    output_dir = client_root / "Output"
    charts_dir = output_dir / "charts"

    output_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)

    projection.to_csv(output_dir / "projection.csv", index=False)

    networth_path = charts_dir / "net_worth.png"
    fig.savefig(networth_path, dpi=300, bbox_inches="tight")

if __name__ == "__main__":
     main()