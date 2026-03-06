import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

def calc_pension(pension_real, retirement, inflation, m):
    pension = 0.0
    if m >= retirement:
        pension= pension_real*(1+inflation)**((m.to_period("M")-retirement.to_period("M")).n/12)
    return pension

def growth(balances, annual_return):                                   
    balances *= (1+annual_return)**(1/12)
    return balances

def balances_at_date(m, balances, balances_actuals=None):
    # balances_actuals: DataFrame indexed by month (Timestamp), columns = accounts
    if balances_actuals is not None and m in balances_actuals.index:
        # align columns to balances index (account names)
        return balances_actuals.loc[m, balances.index].astype(float)
    return balances.copy()

def withdrawal_waterfall(balances, withdrawal, order):
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
    return balances

def cal_withdrawal(
    *, 
    m, 
    withdrawal_start_date, 
    withdrawal_type, 
    balances, 
    withdrawal_rate, 
    order, 
    inflation, 
    annual_w0=None, 
    t0=None, 
    balances_actuals=None
    ):
    
    withdrawal = 0.0
    if m < withdrawal_start_date:
        return balances, withdrawal, annual_w0, t0 

    if withdrawal_type== "VPW":
        withdrawal = float(balances.sum())*float(withdrawal_rate)/12.0
                

    elif withdrawal_type == "4pct":
        if annual_w0 is None:
            if balances_actuals is not None and withdrawal_start_date in balances_actuals.index:
                b0 = balances_actuals.loc[withdrawal_start_date, balances.index].astype(float)
            else:
                b0 = balances.copy()

            annual_w0 = withdrawal_rate * float(b0.sum())
            t0 = withdrawal_start_date

        #Add inflation to withdrawal basis
        delta_months = (m.to_period("M") - t0.to_period("M")).n
        annual_withdrawal = annual_w0*(1+inflation)**(delta_months/12)                  #delta_months is negative
        withdrawal = annual_withdrawal/12.0

    else:
        raise ValueError(f"Unknown withdrawal type: {withdrawal_type}")

    #Take withdrawal from accounts in order
    balances = withdrawal_waterfall(balances, withdrawal, order)
        
    return balances, withdrawal, annual_w0, t0

def apply_flows(balances, cf, m):
    active = cf[(cf["start_date"]<=m) & (cf["end_date"].isna() | (cf["end_date"] >= m))]
    flows = active.groupby("account")["monthly_amount"].sum()
    return balances.add(flows, fill_value=0) 

def calc_real(m, basis, balances, inflation, withdrawal):
    delta_months = (basis.to_period("M") - m.to_period("M")).n          #months since basis is negative
    balances_real = balances*(1+inflation)**(delta_months/12)
    withdrawal_real = withdrawal*(1+inflation)**(delta_months/12)
    return balances_real, withdrawal_real

def calc_taxes(annual_income, income_real):
    std_deduct = 15000
    brackets = {
        11925:0.10, 
        48475:0.12, 
        103350:0.22,
        197300:0.24,
        250525:0.32,
        626350:0.35,
        626351:0.37
    }

    for key in brackets.keys():
        if annual_income<= b:
            monthly_tax = income_real*brackets[b]-std_deduct/12

    return monthly_tax


def projection_engine(start_bal, cf, months, assumptions, balances_actuals = None):
    
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
    
    
    annual_w0 = None
    t0 = None



    #For each month apply: 
    for m in months:
        row = {"Date": m}
        row["Age"] = (m-birthday).days / 365.2425

        #1.apply growth to balances
        balances = growth(balances, annual_return)

        #2. Calculate Income
        #2a. Take Retirement withdrawals

        balances, withdrawal,  annual_w0, t0 = cal_withdrawal(
            m=m, 
            withdrawal_start_date= withdrawal_start_date, 
            withdrawal_type= withdrawal_type, 
            balances=balances, 
            withdrawal_rate=withdrawal_rate, 
            order=order, 
            inflation=inflation, 
            annual_w0=annual_w0,
            t0=t0,
            balances_actuals=balances_actuals
            )

        
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
        income_real = pension_real + withdrawal_real
        tax = calc_taxes
        income_real -=

        
        #5 Calculate Real values
        balances_real, withdrawal_real = calc_real(m, basis, balances, inflation, withdrawal)
        row["Net_Worth_Real"] = balances_real.sum()
        row["Withdrawal_real"] = withdrawal_real
        row["Pension_Real"] = pension_real
        row["Income_Real"] =  income_real


        #7 append record row
        rows.append(row)

    proj = pd.DataFrame(rows)
    return proj