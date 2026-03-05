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





#read config file
#1. load config JSON
scenario_path = Path(sys.argv[1]) if len(sys.argv) >1 else Path("Config/base.json")
cfg = json.loads(scenario_path.read_text(encoding="utf-8"))

#2. Convert config values to proper Python types
assumptions = {"birthday": pd.Timestamp(cfg["birthday"]),
    "annual_return" : cfg["annual_return"],
    "inflation": cfg["inflation"],
    "horizon": pd.Timestamp(cfg["horizon"]),
    "basis": pd.Timestamp(cfg["basis"]),
    "withdrawal_start_date": pd.Timestamp(cfg["withdrawal_start_date"]),
    "withdrawal_rate": cfg["withdrawal_rate"],
    "withdrawal_type": cfg["withdrawal_type"],
    "withdrawal_order": cfg["withdrawal_order"],
    "pension": cfg["pension"],
    "service_length": cfg["service_length"],
    "mra": cfg["mra"],
    "high_3": cfg["high_3"],

}




#read Balances.csv
BALANCES_CSV = Path("/content/drive/MyDrive/Finances/FIRE/Balances.csv")
bal = pd.read_csv(BALANCES_CSV)
bal["Date"] = pd.to_datetime(bal["Date"])
bal = bal.sort_values("Date")              #sort on Date so last month's balances are the last row
latest = bal.iloc[-1]                       #take the last row (last month)

#select last months balances
start_month = latest["Date"].to_period("M").to_timestamp() + pd.DateOffset(months=1)  #start month is the last month plus 1.

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

end_month= ((start_month + pd.DateOffset(years = 30))       #if cashflow end_date is blank, applies rule for 30 years.
    if cf["end_date"].isna().any()
    else last_sched_end
)

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

def plot_accounts(df, ax):              #need to finish adding account balances to plot

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
    ax.plot(df['Date'],df['Income_Real'], label='Real Income', linestyle='dotted', color='g')
    
    # Format Chart Title and Axises
    ax.set_title('Income- Real')
    ax.set_xlabel('Date')
    ax.set_ylabel('($)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"${v/1e3:.2f}k"))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True)
    ax.legend()

#test function
def cal_withdrawal(m, withdrawal_start_date, withdrawal_type, balances, withdrawal_rate, order):
    
    if m >= withdrawal_start_date:
        if withdrawal_type== "VPW":
            withdrawal = balances.sum()*withdrawal_rate/12
            remaining_withdrawal = withdrawal
            row = balances.copy()
            for acct in order:
                
                if row[acct] >= remaining_withdrawal:
                    row[acct] -= remaining_withdrawal
                    remaining_withdrawal = 0
                    break
                else:
                    remaining_withdrawal = remaining_withdrawal-row[acct]
                    row[acct] = 0
            
            balances = row
    else:
        withdrawal = 0
    return balances, withdrawal

def calc_pension(pension_real, retirement, inflation, m):
    pension = 0
    if m >= retirement:
        pension= pension_real*(1+inflation)**((m.to_period("M")-retirement.to_period("M")).n/12)
    return pension

def growth(balances):
    balances *= (1+0.10)**(1/12)
    return balances

def apply_flows(balances, cf, m):
    active = cf[(cf["start_date"]<=m) & (cf["end_date"].isna() | (cf["end_date"] >= m))]
    flows = active.groupby("account")["monthly_amount"].sum()
    return balances.add(flows, fill_value=0) 

def calc_real(m, basis, balances, inflation, withdrawal):
    delta_months = (basis.to_period("M") - m.to_period("M")).n          #months since basis
    balances_real = balances*(1+inflation)**(delta_months/12)
    withdrawal_real = withdrawal*(1+inflation)**(delta_months/12)
    return balances_real, withdrawal_real

def projection_engine(start_bal, cf, months, assumptions):
    
    balances = start_bal.copy()
    rows =[]
    withdrawal = 0

    withdrawal_start_date = assumptions["withdrawal_start_date"]
    withdrawal_rate = assumptions["withdrawal_rate"]
    withdrawal_type = assumptions["withdrawal_type"]
    order = assumptions["withdrawal_order"]
    birthday = assumptions["birthday"]
    inflation = assumptions["inflation"]
    basis = assumptions["basis"]
    retirement = pd.Timestamp("2025-10-01")
    pension_real = assumptions["pension"]
    
    

    #For each month apply: 
    for m in months:
        row = {"Date": m}
        row["Age"] = (m-birthday).days / 365.2425

        #test function
        balances = growth(balances)
        balances, withdrawal = cal_withdrawal(m, withdrawal_start_date, withdrawal_type, balances, withdrawal_rate, order)
        balances = apply_flows(balances, cf, m)
        row.update(balances.to_dict())

        pension = calc_pension(pension_real, retirement, inflation, m)
        row["Pension"] = pension
        row["Income"] = pension + withdrawal
        
        balances_real, withdrawal_real = calc_real(m, basis, balances, inflation, withdrawal)
        row["Net_Worth_Real"] = balances_real.sum()
        row["Withdrawal_real"] = withdrawal_real
        row["Pension_Real"] = pension_real
        row["Income_Real"] = pension_real + withdrawal_real 

        #7 sum net worth  
        
        row["Net_Worth"] = balances.sum()

        #8 append record row
        rows.append(row)

    proj = pd.DataFrame(rows)
    return proj

def main():

    projection = projection_engine(
        start_bal, 
        cf, 
        months, 
        assumptions
    )
    
    print(json.dumps(cfg, indent=2, sort_keys=True))

        # Create two side-by-side subplots
    fig, (ax1, ax2) = plt.subplots(2, 2, figsize=(14, 5), sharex=True)

    # Left Plot: Networth
    plot_networth(projection, ax1)
    plot_accounts(projection, ax1)

    # Right Plot: Income
    plot_income(projection, ax2)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
     main()