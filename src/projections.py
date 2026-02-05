"""
Reads:
    -Balances.csv 
    -cashflow_schedule.csv

Output:
    -projection_nominal.csv

Produces:
    Takes the latest balances applies growth and adds planned cashflows to produce a nominal projection of account balances and networth for the next 30 years. 
    Cashflows also include withdrawals in retirement.

Assumptions:
    Nominal growth rate: 10%
    Retire in Oct 2035
    4% withdrawals begin in Nov 2035


"""

#load packages
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


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

#iterate to build projection
balances = start_bal.copy()
rows =[]
withdrawal_rate = .04
withdrawal = 0

#For each month apply: 
for m in months:
    #1.apply growth to balances
    balances *= (1+0.10/12)
    #2.select active cashflows
    active = cf[(cf["start_date"]<=m) & (cf["end_date"].isna() | (cf["end_date"] >= m))]
    flows = active.groupby("account")["monthly_amount"].sum()

    #3. Take Retirement withdrawals
    if m >= pd.Timestamp("2035-11-01"):
        withdrawal = balances.sum()*withdrawal_rate/12
        balances = balances.multiply(1-withdrawal_rate/12)


    #4. add cashflows to new balances
    balances = balances.add(flows, fill_value=0)

    #5 create record row
    row = {"Date": m, **balances.to_dict()}
    
    #6 sum net worth  
    row["Net_Worth"] = balances.sum() 
    row["Withdrawal"] = withdrawal

    #7 append record row
    rows.append(row)

proj = pd.DataFrame(rows)

out_path = Path("/content/drive/MyDrive/Finances/FIRE/projection_nominal.csv")
proj.to_csv(out_path, index=False) 

proj.head(), out_path