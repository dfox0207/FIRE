import json
import sys
from pathlib import Path
import pandas as pd
import numpy as np

from projection_engine import projection_engine

#read config file
#1. load config JSON
scenario_path = Path(sys.argv[1]) if len(sys.argv) >1 else Path("Config/base.json")
cfg = json.load(scenario_path)

#2. Convert config values to proper Python types
assumptions = {
    "birthday": pd.Timestamp(cfg["birthday"]),
    "annual_return" : cfg["annual_return"],
    "inflation": cfg["inflation"],
    "horizon": pd.Timestamp(cfg["horizon"],
    "basis": pd.Timestamp(cfg["basis"]),
    "withdrawal_start_date": pd.Timestamp(cfg["withdrawal_start_date"]),
    "withdrawal_rate": cfg["withdrawal_rate"],

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

def plot_balances():
    #read BALANCES.CSV
    df = pd.read_csv(BALANCES_CSV, parse_dates=["Date"])            #changed csv_path to BALANCES_CSV

    #identify balance columns (everything except date)
    balance_cols = [c for c in df.columns if c != "Date"]

    #compute net worth per row
    df["net_worth"] = df[balance_cols].sum(axis=1)

    #plot Net Worth Actuals
    df['Date'] = pd.to_datetime(df['Date'])
    plt.plot(df['Date'],df['net_worth'], label='actual', linestyle='-', color='b')
    plt.title('Net Worth- Nominal')
    plt.xlabel('Date')
    plt.ylabel('Net Worth ($)')
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"${v/1e6:.2f}M"))
    plt.grid(True)
    plt.tight_layout()
    

def plot_proj_nom():
    #read projection_nominal.csv
    df = pd.read_csv(PROJ_NOM_CSV, parse_dates=["Date"])            

    #identify balance columns (everything except date)
    balance_cols = [c for c in df.columns if c != "Date"]

    #plot Prjected Net Worth Nominals
    df['Date'] = pd.to_datetime(df['Date'])
    plt.plot(df['Date'],df['Net_Worth'], label='projected', linestyle='dotted', color='r')
    # plt.title('Net Worth')
    # plt.xlabel('Date')
    # plt.ylabel('Net Worth ($)')
    # plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    # plt.xticks(rotation=45)
    # plt.grid(True)
    # plt.tight_layout()
    #plt.show()

def plot_proj_real():
    #read projection_nominal.csv
    df = pd.read_csv(PROJ_NOM_CSV, parse_dates=["Date"])            

    #identify balance columns (everything except date)
    balance_cols = [c for c in df.columns if c != "Date"]

    #plot Prjected Net Worth Nominals
    df['Date'] = pd.to_datetime(df['Date'])
    plt.plot(df['Date'],df['Net_Worth_Real'], label='projected', linestyle='dotted', color='g')
    # plt.title('Net Worth- Real')
    # plt.xlabel('Date')
    # plt.ylabel('Net Worth ($)')
    # plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    # plt.xticks(rotation=45)
    # plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"${v/1e6:.2f}M"))
    # plt.grid(True)
    # plt.tight_layout()
    plt.show()

def plot_withdrawals_real():
    #read projection_nominal.csv
    df = pd.read_csv(PROJ_NOM_CSV, parse_dates=["Date"])            

    #identify balance columns (everything except date)
    balance_cols = [c for c in df.columns if c != "Date"]

    #plot Prjected Net Worth Nominals
    df['Date'] = pd.to_datetime(df['Date'])
    plt.plot(df['Date'],df['Withdrawal_real'], label='projected', linestyle='dotted', color='g')
    plt.title('Withdrawl- Real')
    plt.xlabel('Date')
    plt.ylabel('($)')
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"${v/1e3:.2f}k"))
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def main():

    cfg = 

    projection = projection_engine(
        start_bal= , 
        cf= , 
        months= , 
        assumptions
    )

    plot_balances()
    plot_proj_nom()
    plot_proj_real()
    plot_withdrawals_real()


if __name__ == "__main__":
     main()