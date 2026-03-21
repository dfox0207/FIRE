import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

from tax_engine import tax_engine
from roth_engine import convert_to_roth
from withdraw_engine import calc_withdrawal

from income_types import (
    TaxResult,
    IncomeEvent,
    IncomeSource,
    EarnedIncome,
    RetirementDistributionIncome,
    InterestIncome,
    QualifiedDividendIncome,
    ShortTermCapitalGainIncome,
    LongTermCapitalGainIncome,
    RothDistributionIncome,
    RothConversionIncome,
    SocialSecurityIncome
)

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

def apply_flows(balances, cf, m):
    active = cf[(cf["start_date"]<=m) & (cf["end_date"].isna() | (cf["end_date"] >= m))]
    flows = active.groupby("account")["monthly_amount"].sum()
    return balances.add(flows, fill_value=0) 

def get_active_income_streams(income_streams: pd.DataFrame, m: pd.Timestamp) -> pd.DataFrame:
    return income_streams[
        (income_streams["start_date"]<=m) &
        (income_streams["end_date"].isna() | (income_streams["end_date"]>=m))
    ]

def get_monthly_income_amount(active_streams: pd.DataFrame, source_name: str) -> float:
    rows = active_streams[active_streams["source"] == source_name]

    if rows.empty:
        return 0.0
    if len(rows) == 1:
        return float(rows["monthly_amount"].iloc[0])
    raise ValueError(f"Expected one active row for {source_name}, found {len(rows)}")


def calc_real(m, basis, amount, inflation):
    delta_months = (basis.to_period("M") - m.to_period("M")).n          #months since basis is negative
    amount_real = amount*(1+inflation)**(delta_months/12)
    return amount_real

def summarize_monthly_events(monthly_events):
    spendable_income_real = 0.0
    reported_income_real = 0.0
    monthly_tax_buckets = 0.0

    for event in monthly_events:
        income_type = event.source.income_type
        amount = event.gross_amount

        if income_type.is_spendable():
            spendable_income_real += amount
        if income_type.is_reported_income():
            reported_income_real += amount
        if income_type.is_taxable_event():
            monthly_tax_buckets += income_type.classify_for_tax(amount)
        
    return spendable_income_real, reported_income_real, monthly_tax_buckets

def add_event(monthly_events, m, name, amount, income_type, account=None):
    if amount <=0:
        return 
    monthly_events.append(
        IncomeEvent(
            date=m,
            source=IncomeSource(
                name=name,
                income_type=income_type,
                account=account or name,
            ),
            gross_amount=amount,
        )
    )


def projection_engine(
    account_tax_map, 
    rmd_table,
    start_bal, 
    cf, 
    income_streams,
    months, 
    assumptions, 
    balances_actuals = None
    ):
    
    balances = start_bal.copy()
    rows =[]
    withdrawal = 0.0
    roth_state = {"monthly_conv": None}

    withdrawal_start_date = assumptions["retirement"]
    withdrawal_rate = assumptions["withdrawal_rate"]
    withdrawal_type = assumptions["withdrawal_type"]
    order = assumptions["withdrawal_order"]
    birthday = assumptions["birthday"]
    inflation = assumptions["inflation"]
    basis = assumptions["basis"]
    retirement = pd.Timestamp("2025-10-01")
    annual_return = assumptions["annual_return"]
    service_length = assumptions["service_length"]
    
    filing_status = assumptions["filing_status"]
    
    annual_w0 = None
    t0 = None
    
    ytd_tax = 0.0
    va_ytd_tax = 0.0
    ytd_income_sources= {}
    ytd_tax_buckets = TaxResult.zero()
    ytd_medicare_tax = 0.0
    spendable_income_real = 0.0
    reported_income_real = 0.0
    monthly_tax_buckets = 0.0
    
    

    #For each month apply: 
    for m in months:
        row = {"Date": m}
        age = (m-birthday).days / 365.2425
        row["Age"] = age
        monthly_events = []
        policy = assumptions.get("optimizer_policy", None)
        year_policy = assumptions.get("optimizer_policy", {}).get(m.year, {})
        target_net_income_real = year_policy.get("target_net_income_real", 10000.0)
        roth_target_ordinary_income = year_policy.get("roth_target_ordinary_income", 0.0)
        active_streams = get_active_income_streams(income_streams, m)

        if m.month == 1:
            ytd_tax = 0.0
            va_ytd_tax = 0.0
            ytd_income_sources = {}
            ytd_medicare_tax = 0.0
            ytd_tax_buckets = TaxResult.zero()

            

        #1.apply growth to balances
        balances = growth(balances, annual_return)

        #2. Calculate Income
        income_sources = {}

        # Take Roth Conversion
        roth_conv = convert_to_roth(
            m,
            balances,
            assumptions,
            roth_state,
        )
   
        row["ROTH Conversion"] = roth_conv    
        roth_conv_real = calc_real(m, basis, roth_conv, inflation)

        row["ROTH Conversion Real"] = roth_conv_real
        income_sources["Roth Conversion"] = roth_conv_real

        # Add Salary
        salary_income = get_monthly_income_amount(active_streams, "Penn State Salary")
        row["Penn State Salary Income"] = salary_income
        salary_income_real = calc_real(m, basis, salary_income, inflation)
        row["Penn State Salary Real"] = salary_income_real
        if salary_income_real > 0:
            income_sources["Penn State Salary"] = salary_income_real

        # Add Pension
        pension = get_monthly_income_amount(active_streams, "Pension")
        row["Pension"] = pension
        pension_real = calc_real(m, basis, pension, inflation)
        row["Pension_Real"] = pension_real
        if pension_real > 0:
            income_sources["pension"] = pension_real

        # Take Special Supplemental Annuity
        spec_annuity = get_monthly_income_amount(active_streams, "Special Annuity")
        row["Special Annuity"] = spec_annuity
        spec_annuity_real = calc_real(m, basis, spec_annuity, inflation)
        if spec_annuity_real > 0:
            income_sources["Special Annuity"] = spec_annuity_real

        # Take SSA Annuity
        ssa_annuity = get_monthly_income_amount(active_streams, "SSA")
        row["SSA"] = ssa_annuity
        ssa_annuity_real = calc_real(m, basis, ssa_annuity, inflation)
        row["SSA_Real"] = ssa_annuity_real
        if ssa_annuity_real > 0:
            income_sources["SSA"] = ssa_annuity_real
        
        
       
        #2a. Take Retirement withdrawals
        
        

        balances, income_sources, withdrawal,  annual_w0, t0 = calc_withdrawal(
            m=m, 
            rmd_table=rmd_table,
            account_tax_map=account_tax_map,
            age=age,
            withdrawal_start_date= withdrawal_start_date, 
            withdrawal_type= withdrawal_type, 
            balances=balances, 
            withdrawal_rate=withdrawal_rate, 
            order=order, 
            inflation=inflation, 
            rmd_start_age=73,
            policy = policy,
            ytd_tax_buckets = ytd_tax_buckets,
            annual_w0=annual_w0,
            t0=t0,
            balances_actuals=balances_actuals
            )

        
        row["Withdrawal"] = withdrawal
        withdrawal_real = calc_real(m, basis, withdrawal, inflation)
        row["Withdrawal_real"] = withdrawal_real
        print("row withdrawal", withdrawal)
        
        for key in income_sources:
            income_sources[key] = calc_real(m, basis, income_sources[key], inflation)
        
        brokerage_balance = balances.get("Brokerage", 0.0)
        interest_real= brokerage_balance*assumptions["brokerage_interest_yield"]/12
        qdiv_real=brokerage_balance*assumptions["brokerage_qdiv_yield"]/12
        row["qdiv real"] = qdiv_real
       
        add_event(monthly_events, m, "Brokerage Interest", interest_real, InterestIncome(), "Brokerage")
        add_event(monthly_events, m, "Brokerage Qualified Dividends", qdiv_real, QualifiedDividendIncome(), "Brokerage")
        
        brokerage_withdrawal = income_sources.get("Brokerage", 0.0)
        if brokerage_withdrawal > 0:
            ltcg_ratio= assumptions.get("brokerage_ltcg_realization_ratio", 0.30)
            ltcg_amount= brokerage_withdrawal*ltcg_ratio
            add_event(
                monthly_events,
                m,
                "Brokerage LTCG Withdrawal",
                ltcg_amount,
                LongTermCapitalGainIncome(),
                "Brokerage",
            )
        

        

        for key in income_sources:
            ytd_income_sources[key] = ytd_income_sources.get(key, 0) + income_sources[key]
        
        for event in monthly_events:
            if event.source.income_type.is_spendable():
                spendable_income_real += event.gross_amount
            
            tax_result = event.source.income_type.tax(event.gross_amount)
            monthly_tax_buckets.add(tax_result)

            
            source = IncomeSource(
                name=f"{acct} Withdrawal",
                income_type=income_type,
                account=acct
            )

            monthly_events.append(
                IncomeEvent(
                    date=m,
                    source=source,
                    gross_amount=amount
                )
            )
        
        add_event(monthly_events, m, "Penn State Salary", salary_income_real, EarnedIncome(), "Penn State Salary")
        add_event(monthly_events, m, "FERS", pension_real, RetirementDistributionIncome(), "FERS")
        add_event(monthly_events, m, "Roth Conversion", roth_conv_real, RothConversionIncome(), "roth_conversion")
        add_event(monthly_events, m, "Special Annuity", spec_annuity_real, RetirementDistributionIncome(), "Special Annuity")
        add_event(monthly_events, m, "Social Security", ssa_annuity_real, SocialSecurityIncome(), "SSA")


       
        row["interest real"] = interest_real
        monthly_tax_buckets = TaxResult.zero()
        for event in monthly_events: monthly_tax_buckets.add(event.tax_result())
        ytd_tax_buckets.add(monthly_tax_buckets)

        # Sum Total Income
        row["Income"] = (pension + withdrawal + spec_annuity + ssa_annuity + salary_income)
        income_real = sum(amt for key, amt in income_sources.items() if key !="roth_conversion")
        row["Income_Real"] =  income_real
        print("row income real", income_real)
        #3. add cashflows to new balances
        balances = apply_flows(balances, cf, m)
        row.update(balances.to_dict())
        balances_real = calc_real(m, basis, balances, inflation)

        #4 sum net worth  
        row["Net_Worth"] = balances.sum() 
        row["Net_Worth_Real"] = balances_real.sum()   
        
       
        
        
        #6. Calculate Taxes
        tax, ytd_tax, va_tax, va_ytd_tax, medicare_tax, ytd_medicare_tax = tax_engine(
            tax_buckets=ytd_tax_buckets,                             
            ytd_tax = ytd_tax,
            va_ytd_tax = va_ytd_tax,
            ytd_medicare_tax=ytd_medicare_tax,
            filing_status = assumptions.get("filing_status", "mfs"),
        )
        row["Fed Tax"] = tax 
        row["Medicare Tax"] = medicare_tax
        row["VA Tax"] = va_tax
        total_tax = tax + va_tax + medicare_tax
        row["Total Tax"] = total_tax
        net_income_real = income_real - total_tax
        row["Net_Income_Real"] = net_income_real

        
        #7 append record row
        rows.append(row)

    proj = pd.DataFrame(rows)
    return proj