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
    "withdrawl_order": cfg["withdrawl_order"],
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
            
            rows.append(row.copy())
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


def projection_engine(start_bal, cf, months, assumptions):
    
    balances = start_bal.copy()
    rows =[]
    withdrawal = 0

    withdrawal_start_date = assumptions["withdrawal_start_date"]
    withdrawal_rate = assumptions["withdrawal_rate"]
    withdrawal_type = assumptions["withdrawal_type"]
    order = assumptions["withdrawl_order"]
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

    print(projection)

if __name__ == "__main__":
     main()