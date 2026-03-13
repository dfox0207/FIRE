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

def calc_spec_annuity(m, birthday, ssa_benefit, service_length):
    if birthday + pd.DateOffset(years=57) <= m <= birthday + pd.DateOffset(years=62):
        spec_annuity = ssa_benefit * service_length/40
    else:
        spec_annuity = 0
    return spec_annuity

def calc_ssa(m, birthday, ssa_benefit, inflation, basis):
    if m > birthday + pd.DateOffset(years=62):
        ssa_annuity = ssa_benefit*0.8*(1+inflation)**(((m.to_period("M") - basis.to_period("M")).n)/12)
        ssa_annuity_real = ssa_benefit*0.8
    else:
        ssa_annuity = 0
        ssa_annuity_real = 0
    return ssa_annuity, ssa_annuity_real

def calc_real(m, basis, amount, inflation):
    delta_months = (basis.to_period("M") - m.to_period("M")).n          #months since basis is negative
    amount_real = amount*(1+inflation)**(delta_months/12)
    return amount_real

def income_type_from_account(acct: str, account_tax_map, event_kind:str | None=None):
    account_type = account_tax_map.loc[acct, "account_type"]

    if account_type in {"401k", "403b", "457b", "traditional_ira", "annuity", "tsp"}:
        return RetirementDistributionIncome()

    if account_type in {"roth_conv", "salary"}:
        return EarnedIncome()

    if account_type in {"roth_ira", "roth_401k", "roth_tsp"}:
        return RothDistributionIncome()
    
    if account_type == "brokerage":
        return None
        # if event_kind == "interest":
        #     return InterestIncome()
        # elif event_kind == "qualified_dividend":
        #     return QualifiedDividendIncome()
        # elif event_kind == "ltcg":
        #     return LongTermCapitalGainIncome()
        # else:
        #     raise ValueError(f"Brokerage requires event_kind, got {event_kind}")
    raise ValueError(f"Unknown account_type: {account_type}")



def projection_engine(
    account_tax_map, 
    start_bal, 
    cf, 
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
    pension_real = assumptions["pension"]
    annual_return = assumptions["annual_return"]
    service_length = assumptions["service_length"]
    ssa_benefit = assumptions["ssa_benefit"]
    
    annual_w0 = None
    t0 = None
    
    ytd_tax = 0.0
    va_ytd_tax = 0.0
    ytd_income_sources= {}
    ytd_tax_buckets = TaxResult.zero()

    #For each month apply: 
    for m in months:
        row = {"Date": m}
        row["Age"] = (m-birthday).days / 365.2425
        monthly_events = []
        
        

        if m.month == 1:
            ytd_tax = 0.0
            va_ytd_tax = 0.0
            ytd_income_sources = {}
            ytd_tax_buckets = TaxResult.zero()
            

        #1.apply growth to balances
        balances = growth(balances, annual_return)

        #2. Calculate Income
        #2a. Take Retirement withdrawals

        balances, income_sources, withdrawal,  annual_w0, t0 = calc_withdrawal(
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
        withdrawal_real = calc_real(m, basis, withdrawal, inflation)
        row["Withdrawal_real"] = withdrawal_real

        for key in income_sources:
            income_sources[key] = calc_real(m, basis, income_sources[key], inflation)
        
        brokerage_balance = balances.get("Brokerage", 0.0)
        interest_real= brokerage_balance*assumptions["brokerage_interest_yield"]/12
        qdiv_real=brokerage_balance*assumptions["brokerage_qdiv_yield"]/12
        row["qdiv real"] = qdiv_real
        if interest_real>0:
            monthly_events.append(
                IncomeEvent(
                    date=m,
                    source=IncomeSource(
                        name="Brokerage Interest",
                        income_type=InterestIncome(),
                        account="Brokerage"
                    ),
                    gross_amount=income_real
                )
            )
        if qdiv_real>0:
            monthly_events.append(
                IncomeEvent(
                    date=m,
                    source=IncomeSource(
                        name="Brokerage Qualified Dividends",
                        income_type=QualifiedDividendIncome(),
                        account="Brokerage"
                    ),
                    gross_amount=qdiv_real
                )
            )
        brokerage_withdrawal=income_sources.get("Brokerage", 0.0)
        if brokerage_withdrawal>0:
            ltcg_ratio=assumptions["brokerage_ltcg_realization_ratio"]
            ltcg_amount=brokerage_withdrawal*ltcg_ratio
            if ltcg_amount>0:
                monthly_events.append(
                    IncomeEvent(
                        date=m,
                        source=IncomeSource(
                            name="Brokerage LTCG",
                            income_type=LongTermCapitalGainIncome(),
                            account="Brokerage"
                        ),
                        gross_amount=ltcg_amount
                    )
                )

        #2b. Take Roth Conversion
        roth_conv = convert_to_roth(
            m,
            balances,
            assumptions,
            roth_state,
        )
   
        row["ROTH Conversion"] = roth_conv    
        roth_conv_real = calc_real(m, basis, roth_conv, inflation)

        row["ROTH Conversion Real"] = roth_conv_real
        income_sources["TSP"] = income_sources.get("TSP", 0.0) + roth_conv_real

        #2c. Take Pension
        pension = calc_pension(pension_real, retirement, inflation, m)
        row["Pension"] = pension
        row["Pension_Real"] = pension_real
        income_sources["FERS"] = pension_real

        #2d. Take Special Supplemental Annuity/SSA Annuity
        spec_annuity = calc_spec_annuity(m, birthday, ssa_benefit, service_length)
        ssa_annuity, ssa_annuity_real = calc_ssa(m, birthday, ssa_benefit, inflation, basis)
        income_sources["Special Annuity"] = spec_annuity
        income_sources["SSA Annuity"] = ssa_annuity_real
        
        
        #2e. Sum Total Income
        row["Income"] = pension + withdrawal + spec_annuity + ssa_annuity
        income_real = pension_real + withdrawal_real + ssa_annuity_real + interest_real + qdiv_real
        row["Income_Real"] =  income_real
        

        for key in income_sources:
            ytd_income_sources[key] = ytd_income_sources.get(key, 0) + income_sources[key]
        
        for acct, amount in income_sources.items():
            if amount <= 0:
                continue

            if acct == "Brokerage":
                continue
            
            income_type = income_type_from_account(acct, account_tax_map)
            if income_type is None:
                continue

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
        if pension_real > 0 :
            monthly_events.append(
                IncomeEvent(
                    date=m,
                    source=IncomeSource(
                        name="Pension",
                        income_type=RetirementDistributionIncome(),
                        account="Pension"
                    ),
                    gross_amount = pension_real
                )
            )
        
        brokerage_withdrawal = income_sources.get("Brokerage", 0.0)

        if brokerage_withdrawal > 0:
            ltcg_ratio= assumptions.get("brokerage_ltcg_ratio", 0.30)
            ltcg_amount= brokerage_withdrawal*ltcg_ratio
            if ltcg_amount>0:
                brokerage_ltcg_source = IncomeSource(
                    name="Brokerage LTCG Withdrawal", 
                    income_type=LongTermCapitalGainIncome(), 
                    account="Brokerage"
                )
                monthly_events.append(
                    IncomeEvent(
                        date=m,
                        source=brokerage_ltcg_source,
                        gross_amount=ltcg_amount
                    )
                )
        if m.year== 2036 and m.month ==1:
            print("Date:",m)
            print("Brokerage withdrawal:", income_sources.get("Brokerage", 0.0))
            print("Ordinary Income: ", monthly_tax_buckets.federal_ordinary_income)
            print("LTCG income:", monthly_tax_buckets.federal_ltcg_income)
            print("QDIV income", monthly_tax_buckets.federal_qualified_dividends)
            print("EVENTS:")
            for e in monthly_events:
                print(e.source.name, e.gross_amount)
        #row["ltcg amount"] =ltcg_amount.gross_amount
        row["interest real"] = interest_real
        monthly_tax_buckets = TaxResult.zero()
        for event in monthly_events: monthly_tax_buckets.add(event.tax_result())
        ytd_tax_buckets.add(monthly_tax_buckets)

        
        #3. add cashflows to new balances
        balances = apply_flows(balances, cf, m)
        row.update(balances.to_dict())
        balances_real = calc_real(m, basis, balances, inflation)

        #4 sum net worth  
        row["Net_Worth"] = balances.sum() 
        row["Net_Worth_Real"] = balances_real.sum()   
        
       
        
        
        #6. Calculate Taxes
        tax, ytd_tax, va_tax, va_ytd_tax = tax_engine(
            tax_buckets=ytd_tax_buckets,                             
            ytd_tax = ytd_tax,
            va_ytd_tax = va_ytd_tax
        )
        row["Fed Tax"] = tax 
        row["VA Tax"] = va_tax
        total_tax = tax + va_tax
        row["Total Tax"] = total_tax
        net_income_real = income_real - total_tax
        row["Net_Income_Real"] = net_income_real

        
        #7 append record row
        rows.append(row)

    proj = pd.DataFrame(rows)
    return proj