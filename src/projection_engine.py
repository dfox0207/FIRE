import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

from tax_engine import tax_engine
from roth_engine import convert_to_roth
from withdraw_engine import calc_withdrawal
from optimizer import random_search_optimizer, build_annual_summary

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
    SocialSecurityIncome,
    income_type_from_event_type,
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
    if source_name not in active_streams.index:
        return 0.0

    rows = active_streams.loc[[source_name]]
    return float(rows["monthly_amount"].sum())


def calc_real(m, basis, amount, inflation):
    delta_months = (basis.to_period("M") - m.to_period("M")).n          #months since basis is negative
    amount_real = amount*(1+inflation)**(delta_months/12)
    return amount_real

def calc_nominal(m, basis, amount, inflation):
    delta_months = (m.to_period("M") - basis.to_period("M")).n          #months since basis is positive
    amount_nominal = amount*(1+inflation)**(delta_months/12)
    return amount_nominal

def summarize_monthly_events(monthly_events):
    spendable_income_real = 0.0
    reported_income_real = 0.0
    monthly_tax_buckets = TaxResult.zero()

    for event in monthly_events:
        income_type = event.source.income_type
        amount = event.gross_amount

        if income_type.is_spendable():
            spendable_income_real += amount
        if income_type.is_reported_income():
            reported_income_real += amount
        if income_type.is_taxable_income():
            monthly_tax_buckets.add(event.tax_result())
        
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
    account_meta, 
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
    retirement = assumptions["retirement"]
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

            

        # Apply growth to balances
        balances = growth(balances, annual_return)
        balances_real = calc_real(m, basis, balances, inflation)

        # Calculate Income
        income_sources = {}

        # Add Salary
        salary_income = get_monthly_income_amount(active_streams, "Penn State Salary")
        salary_income_real = calc_real(m, basis, salary_income, inflation)
        if salary_income_real > 0:
            income_sources["Penn State Salary"] = salary_income_real
        row["Penn State Salary Income"] = salary_income
        row["Penn State Salary Real"] = salary_income_real
        

        # Add Pension
        pension = get_monthly_income_amount(active_streams, "Pension")
        pension_real = calc_real(m, basis, pension, inflation)
        if pension_real > 0:
            income_sources["Pension"] = pension_real
        row["Pension"] = pension
        row["Pension_Real"] = pension_real
        

        # Take Special Supplemental Annuity
        spec_annuity = get_monthly_income_amount(active_streams, "Special Annuity")
        spec_annuity_real = calc_real(m, basis, spec_annuity, inflation)
        if spec_annuity_real > 0:
            income_sources["Special Annuity"] = spec_annuity_real
        row["Special Annuity"] = spec_annuity
        
        
        # Take SSA Annuity
        ssa_annuity = get_monthly_income_amount(active_streams, "SSA Benefit")
        ssa_annuity_real = calc_real(m, basis, ssa_annuity, inflation)
        if ssa_annuity_real > 0:
            income_sources["SSA Benefit"] = ssa_annuity_real
        row["SSA"] = ssa_annuity
        row["SSA_Real"] = ssa_annuity_real
        
       
        #2a. Take Retirement withdrawals
        policy = None
        if withdrawal_type == "Optimizer":
            result = random_search_optimizer(
                account_meta=account_meta,
                rmd_table=rmd_table,
                start_bal=start_bal,
                cf=cf,
                income_streams=income_streams,
                months=months,
                assumptions=assumptions,
                balances_actuals=balances_actuals,
                target_annual_net_income_real=100000.0,
                block_size=5,
                n_trials=200,
                roth_min=0.0,
                roth_max=150000.0,
                seed=42,
            )

            print("Best score:", result["best_score"])
            print("Best policy:", result["best_policy"])

            policy = result["best_policy"]
            annual_summary = build_annual_summary(projection)

            
        balances_real, withdrawal_sources, withdrawal,  annual_w0, t0 = calc_withdrawal(
            m=m, 
            rmd_table=rmd_table,
            account_meta=account_meta,
            age=age,
            withdrawal_start_date= withdrawal_start_date, 
            withdrawal_type= withdrawal_type, 
            balances=balances,
            balances_real=balances_real, 
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
        
        withdrawal_sources_real = {acct: calc_real(m, basis, amt, inflation) for acct, amt in withdrawal_sources.items()}
        income_sources.update(withdrawal_sources_real)
        row["Withdrawal"] = withdrawal
        row["Withdrawal_real"] = calc_real(m, basis, withdrawal, inflation)

        # Take Roth Conversion
        roth_conv = convert_to_roth(m, balances, assumptions, roth_state)
        roth_conv_real = calc_real(m, basis, roth_conv, inflation)
        income_sources["Roth Conversion"] = roth_conv_real
        row["ROTH Conversion"] = roth_conv 
        row["ROTH Conversion Real"] = roth_conv_real
                
        
        # Brokerage Flows
        brokerage_balance_real = balances_real.get("Brokerage", 0.0)
        interest_real= brokerage_balance_real * assumptions["brokerage_interest_yield"]/12
        qdiv_real=brokerage_balance_real*assumptions["brokerage_qdiv_yield"]/12

        if interest_real >0:
            income_sources["Brokerage Interest"] = interest_real
        if qdiv_real >0:
            income_sources["Brokerage Qualified Dividends"] = qdiv_real
        
        brokerage_withdrawal = withdrawal_sources.get("Brokerage", 0.0)
        if brokerage_withdrawal > 0:
            ltcg_ratio= assumptions.get("brokerage_ltcg_realization_ratio")
            ltcg_amount= brokerage_withdrawal * ltcg_ratio
            if ltcg_amount > 0:
                income_sources["Brokerage LTCG Withdrawal"] = ltcg_amount
            
        row["qdiv real"] = qdiv_real
        row["interest real"] = interest_real

        # Create Monthly Income Events
        for source_name, amount in income_sources.items():
            if amount <= 0:
                continue
            
            event_type = account_meta.loc[source_name, "event_type"]
            income_type = income_type_from_event_type(event_type)

            if income_type is None:
                continue

            add_event(monthly_events, m, source_name, amount, income_type)
            
        


        # Summarize Events
        income_real, reported_income_real, monthly_tax_buckets = summarize_monthly_events(monthly_events)
        ytd_tax_buckets.add(monthly_tax_buckets)

        row["Income"] = (pension + withdrawal + spec_annuity + ssa_annuity + salary_income)
        income_real = sum(event.gross_amount for event in monthly_events if event.source.income_type.is_spendable())
        row["Income_Real"] =  income_real
        
        #3. add cashflows to new balances
        balances_real = apply_flows(balances_real, cf, m)
        row.update(balances_real.to_dict())
        balances = calc_nominal(m, basis, balances_real, inflation)
        row.update(balances.to_dict())

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