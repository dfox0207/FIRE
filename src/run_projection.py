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
from optimizer import random_search_optimizer, pretty_print_policy



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
    "pension": cfg["pension"],
    "service_length": cfg["service_length"],
    "mra": cfg["mra"],
    "high_3": cfg["high_3"],
    "ssa_benefit": cfg["ssa_benefit"],
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

#read account_meta.csv
ACCOUNT_META_CSV = Path("/content/FIRE/Config/account_meta.csv")
acct_meta = pd.read_csv(ACCOUNT_META_CSV)
acct_meta["account"] = acct_meta["account"].str.strip()
account_tax_map = acct_meta.set_index("account")

UNIFORM_LIFETIME_TABLE_CSV = Path("/content/FIRE/Config/uniform_lifetime_table.csv")
rmd_df = pd.read_csv(UNIFORM_LIFETIME_TABLE_CSV)
rmd_table = dict(zip(rmd_df["age"].astype(int), rmd_df["divisor"].astype(float)))



def main():

    projection = projection_engine(
        account_tax_map,
        rmd_table,
        start_bal, 
        cf, 
        months, 
        assumptions,
        balances_actuals = bal
    )

    
    print(json.dumps(cfg, indent=2, sort_keys=True))

    fig = plotting(projection, assumptions["withdrawal_order"], BALANCES_CSV)

    result = random_search_optimize(
        start_bal=start_bal,
        cf=cf,
        months=months,
        assumptions=assumptions,
        balances_actuals=balances_actuals,
        account_tax_map=account_tax_map,
        rmd_table=rmd_table,
        n_iter=200,
        objective="terminal_wealth",
        min_monthly_income_real=10000.0,
        income_bounds=(10000.0, 18000.0),
        roth_bounds=(0.0, 120000.0),
    )

    print("Best score:", result.best_score)
    pretty_print_policy(result.best_policy)

    best_df = result.best_projection

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