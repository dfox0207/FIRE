import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

def calc_pension(pension_real, retirement, inflation, m):
    pension = 0.0
    if m >= retirement:
        pension= pension_real*(1+inflation)**((m.to_period("M")-retirement.to_period("M")).n/12)
    return pension

def growth(balances, annual_return):                                   #done
    balances *= (1+annual_return)**(1/12)
    return balances

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
    withdrawal = 0.0

    withdrawal_start_date = assumptions["withdrawal_start_date"]
    withdrawal_rate = assumptions["withdrawal_rate"]
    withdrawal_type = assumptions["withdrawal_type"]
    order = assumptions["withdrawal_order"]
    birthday = assumptions["birthday"]
    inflation = assumptions["inflation"]
    basis = assumptions["basis"]
    retirement = pd.Timestamp("2025-10-01")
    pension_real = assumptions["pension"]
    annual_return = assumptions["annual_return"]
    
    

    #For each month apply: 
    for m in months:
        row = {"Date": m}
        row["Age"] = (m-birthday).days / 365.2425

        #1.apply growth to balances
        balances = growth(balances)

        #2. Calculate Income
        #2a. Take Retirement withdrawals
        balances, withdrawal = cal_withdrawal(m, withdrawal_start_date, withdrawal_type, balances, withdrawal_rate, order)
        row["Withdrawal"] = withdrawal
       
        #2b. Take Pension
        pension = calc_pension(pension_real, retirement, inflation, m)
        row["Pension"] = pension

        #2c. Sum Total Income
        row["Income"] = pension + withdrawal
        
        #3. add cashflows to new balances
        balances = apply_flows(balances, cf, m)
        row.update(balances.to_dict())

        #4 sum net worth  
        row["Net_Worth"] = balances.sum() 
        
        #5 Calculate Real values
        balances_real, withdrawal_real = calc_real(m, basis, balances, inflation, withdrawal)
        row["Net_Worth_Real"] = balances_real.sum()
        row["Withdrawal_real"] = withdrawal_real
        row["Pension_Real"] = pension_real
        row["Income_Real"] = pension_real + withdrawal_real 


        #7 append record row
        rows.append(row)

    proj = pd.DataFrame(rows)
    return proj