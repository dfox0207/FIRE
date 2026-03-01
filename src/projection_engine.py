import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

def pension(pension_real):
    if m >= retirement:
        pension= pension_real*(1+inflation)**((m.to_period("M")-retirement.to_period("M")).n/12)
    return pension

def growth(balances):                                   #done
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
        #1.apply growth to balances
        balances = growth(balances)

        #2.

        #3. Calculate Income
        #3a. Take Retirement withdrawals
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

       
        #3b. Take Pension
        if m >= retirement:
            pension= pension_real*(1+inflation)**((m.to_period("M")-retirement.to_period("M")).n/12)
        
        


        #4. add cashflows to new balances
        balances = apply_flows(balances, cf, m)
        
        #5 Calculate Real values
        delta_months = (basis.to_period("M") - m.to_period("M")).n          #months since basis
        balances_real = balances*(1+inflation)**(delta_months/12)
        withdrawal_real = withdrawal*(1+inflation)**(delta_months/12)

        #6 create record row
        row = {"Date": m, **balances.to_dict()}
        
        #7 sum net worth  
        row["Net_Worth"] = balances.sum() 
        row["Withdrawal"] = withdrawal
        row["Pension"] = pension
        row["Income"] = pension + withdrawal
        row["Age"] = (m-birthday).days / 365.2425
        row["Net_Worth_Real"] = balances_real.sum()
        row["Withdrawal_real"] = withdrawal_real
        row["Pension_Real"] = pension_real
        row["Income_Real"] = pension_real + withdrawal_real 

        #8 append record row
        rows.append(row)

    proj = pd.DataFrame(rows)
    return proj