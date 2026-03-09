import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

from tax_engine import tax_engine

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

def calc_roth_conv(balance, annual_return, retirement, birthday):
    start_date = retirement
    end_date = birthday + pd.DateOffset(years=75)
    conv_window = end_date - start_date
    r = (1 + annual_return)**(1/12) - 1
    roth_conv = balance *r/(1-(1+r)**(-conv_window))

    return roth_conv


def calc_taxes(ytd_income_real, ytd_tax, va_ytd_tax):


    #1. Federal Taxes
    std_deduct = 15000
    brackets = [
        (0,0.10), 
        (11925,0.12), 
        (48475,0.22),
        (103350,0.24),
        (197300,0.32),
        (250525,0.35),
        (626350,0.37)
    ]
    
    new_ytd_taxable_income = max(0.0, ytd_income_real - std_deduct)
    last_ytd_tax = ytd_tax
    
    new_ytd_tax = 0
    
    for i in range(len(brackets)):
        
        lower, lower_rate = brackets[i]
        if i+1 < len(brackets):
            upper = brackets[i+1][0]
            
        else:
            upper = float("inf")   

        if new_ytd_taxable_income >= upper:
            tax_i = (upper - lower) * lower_rate
            
        elif new_ytd_taxable_income > lower:
            tax_i = (new_ytd_taxable_income - lower) * lower_rate
        
            

            
    
        else:
            break
    
        new_ytd_tax += tax_i
    
    new_tax = new_ytd_tax - last_ytd_tax

    #2. VA Taxes
    va_std_deduct = 8750
    va_brackets = [
        (0, 0.02, 0),
        (3001, 0.03, 60),
        (5001, 0.05, 120),
        (17000, 0.0575, 720)
    ]

    new_va_taxable_income = max(0.0, ytd_income_real - va_std_deduct)
    last_va_ytd_tax = va_ytd_tax

    new_va_ytd_tax = 0

    for i in range(len(va_brackets)):
        va_lower, va_lower_rate, va_lower_amount = va_brackets[i]
        if i+1 < len(va_brackets):
            va_upper = va_brackets[i+1][0]
        else:
            va_upper = float("inf")
            

        if va_lower <= new_va_taxable_income > va_upper:
            va_tax_i = (va_upper - va_lower) * va_lower_rate
            
        elif va_lower <= new_va_taxable_income < va_upper:
            va_tax_i = (new_va_taxable_income - va_lower) * va_lower_rate + va_lower_amount  
        
            new_va_ytd_tax += va_tax_i

            break 
    new_va_tax = new_va_ytd_tax - last_va_ytd_tax
    

    return new_tax, new_va_tax, new_ytd_tax, new_va_ytd_tax


     

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
    service_length = assumptions["service_length"]
    ssa_benefit = assumptions["ssa_benefit"]
    
    annual_w0 = None
    t0 = None
    roth_conv= 0.0
    ytd_tax = 0.0
    va_ytd_tax = 0.0
    ytd_income_real = 0.0

    #For each month apply: 
    for m in months:
        row = {"Date": m}
        row["Age"] = (m-birthday).days / 365.2425

        if m.month == 1:
            ytd_tax = 0.0
            va_ytd_tax = 0.0
            ytd_income_real = 0.0

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

        #2b. Take Roth Conversion
        if m == retirement:
            roth_conv = calc_roth_conv(
                balances["TSP"],
                annual_return,
                retirement,
                birthday
            )

        if retirement <= m <= birthday + pd.DateOffset(years=75):
            balances["TSP"] -= roth_conv
            
       
        #2c. Take Pension
        pension = calc_pension(pension_real, retirement, inflation, m)
        row["Pension"] = pension

        #2d. Take Special Supplemental Annuity
        
        if birthday + pd.DateOffset(years=57) <= m <= birthday + pd.DateOffset(years=62):
            spec_annuity = ssa_benefit * service_length/40

        elif m > birthday + pd.DateOffset(years=62):
            ssa_annuity = ssa_benefit*0.8*(1+inflation)**(((m.to_period("M") - basis.to_period("M")).n)/12)
            ssa_annuity_real = ssa_benefit*0.8
        else:
            spec_annuity = 0
            ssa_annuity = 0
            ssa_annuity_real = 0
        
        #2e. Sum Total Income
        row["Income"] = pension + withdrawal + spec_annuity + ssa_annuity
        
        #3. add cashflows to new balances
        balances = apply_flows(balances, cf, m)
        row.update(balances.to_dict())

        #4 sum net worth  
        row["Net_Worth"] = balances.sum() 


        
        #5 Calculate Real values
        balances_real, withdrawal_real = calc_real(m, basis, balances, inflation, withdrawal)
        income_real = pension_real + withdrawal_real + ssa_annuity_real
        ytd_income_real += income_real

        tax, ytd_tax, va_tax, va_ytd_tax = tax_engine(
            ytd_income_real = ytd_income_real,
            ytd_tax = ytd_tax,
            va_ytd_tax = va_ytd_tax
        )

        total_tax = tax + va_tax
        net_income_real = income_real - total_tax
        

        row["Net_Worth_Real"] = balances_real.sum()
        row["Withdrawal_real"] = withdrawal_real
        row["Pension_Real"] = pension_real
        row["Income_Real"] =  income_real
        row["Fed Tax"] = tax 
        row["VA Tax"] = va_tax  
        row["Total Tax"] = total_tax
        row["Net_Income_Real"] = net_income_real


        #7 append record row
        rows.append(row)

    proj = pd.DataFrame(rows)
    return proj