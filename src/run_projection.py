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
from plotting import plotting
from optimizer import random_search_optimizer, build_annual_summary



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
    "retirement": pd.Timestamp(cfg["retirement"]),
    "withdrawal_rate": cfg["withdrawal_rate"],
    "withdrawal_type": cfg["withdrawal_type"],
    "withdrawal_order": cfg["withdrawal_order"],
    "service_length": cfg["service_length"],
    "mra": cfg["mra"],
    "high_3": cfg["high_3"],
    "brokerage_interest_yield": cfg["brokerage_interest_yield"],
    "brokerage_qdiv_yield": cfg["brokerage_qdiv_yield"],
    "brokerage_ltcg_realization_ratio": cfg["brokerage_ltcg_realization_ratio"],
    "filing_status": cfg["filing_status"]

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

#read income_streams.csv
INCOME_STREAMS_CSV = Path("/content/drive/MyDrive/Finances/FIRE/income_streams.csv")
income_streams = pd.read_csv(INCOME_STREAMS_CSV).set_index("source")
income_streams.index= income_streams.index.astype(str).str.strip()
income_streams["start_date"]= pd.to_datetime(income_streams["start_date"]).dt.to_period("M").dt.to_timestamp() + pd.DateOffset(months=1)
income_streams["end_date"]= pd.to_datetime(income_streams["end_date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
income_streams["monthly_amount"]= pd.to_numeric(income_streams["monthly_amount"]).fillna(0.0)
income_streams["source_type"]= income_streams["source_type"].astype(str).str.strip()
if income_streams["end_date"].notna().any():
    last_sched_end = income_streams["end_date"].dropna().max()
else:
    last_sched_end = pd.NaT 

end_month= assumptions["horizon"]

income_streams_months = pd.date_range(start_month, end_month, freq="MS")


#read account_meta.csv
ACCOUNT_META_CSV = Path("/content/FIRE/Config/account_meta.csv")
account_meta = pd.read_csv(ACCOUNT_META_CSV)
account_meta["name"] = account_meta["name"].astype(str).str.strip()
account_meta["event_type"] = account_meta["event_type"].astype(str).str.strip().lower()
account_meta = account_meta.set_index("name")

#read Uniform Lifetime Table
UNIFORM_LIFETIME_TABLE_CSV = Path("/content/FIRE/Config/uniform_lifetime_table.csv")
rmd_df = pd.read_csv(UNIFORM_LIFETIME_TABLE_CSV)
rmd_table = dict(zip(rmd_df["age"].astype(int), rmd_df["divisor"].astype(float)))



def main():

    if assumptions["withdrawal_type"].lower() == "optimizer":
        result = random_search_optimizer(
            account_meta=account_meta,
            rmd_table=rmd_table,
            start_bal=start_bal,
            cf=cf,
            income_streams=income_streams,
            months=months,
            assumptions=assumptions,
            balances_actuals=bal,
            target_annual_net_income_real=100000.0,
            block_size=5,
            n_trials=200,
            roth_min=0.0,
            roth_max=150000.0,
            seed=42,
        )

        print("Best score:", result["best_score"])
        print("Best policy:", result["best_policy"])

        assumptions["optimizer_policy"] = result["best_policy"]
        projection = projection_engine(
            account_meta=account_meta,
            rmd_table=rmd_table,
            start_bal= start_bal, 
            cf=cf, 
            income_streams=income_streams,
            months=months, 
            assumptions=assumptions,
            balances_actuals = bal,
        )
        annual_summary = build_annual_summary(projection)
    else:
        projection = projection_engine(
            account_meta=account_meta,
            rmd_table=rmd_table,
            start_bal= start_bal, 
            cf=cf, 
            income_streams=income_streams,
            months=months, 
            assumptions=assumptions,
            balances_actuals = bal,
        )
        annual_summary = build_annual_summary(projection)



    annual = projection.copy()
    annual["Year"] = pd.to_datetime(annual["Date"]).dt.year
    annual_summary = annual.groupby("Year", as_index=False).agg({
        "Income": "sum",
        "Income_Real": "sum",
        "Net_Income_Real": "sum",
        "Fed Tax": "sum",
        "VA Tax": "sum",
        "Medicare Tax": "sum" if "Medicare Tax" in annual.columns else "sum",
        "Total Tax": "sum",
        "Net_Worth": "last",
        "Net_Worth_Real": "last",
    })

    
    print(json.dumps(cfg, indent=2, sort_keys=True))

    fig = plotting(projection, annual_summary, assumptions["withdrawal_order"], BALANCES_CSV)

    

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