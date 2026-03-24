import json
from pathlib import Path
from typing import Dict, Tuple
from dataclasses import replace

import numpy as np
import pandas as pd

def load_brackets(csv_path: str | Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    df = pd.read_csv(csv_path)

    # Convert "inf" text in upper column to np.inf
    df["upper"] = df["upper"].replace("inf", np.inf)
    df["upper"] = pd.to_numeric(df["upper"], errors="coerce")
    df["lower"] = pd.to_numeric(df["lower"], errors="raise")
    df["rate"] = pd.to_numeric(df["rate"], errors="raise")
    df["fee"] = pd.to_numeric(df["fee"], errors="raise")

    lowers = df["lower"].to_numpy(dtype=float)
    uppers = df["upper"].to_numpy(dtype=float)
    rates = df["rate"].to_numpy(dtype=float)
    fees = df["fee"].to_numpy(dtype=float)

    uppers = np.where(np.isnan(uppers), np.inf, uppers)

    return lowers, uppers, rates, fees


def load_tax_systems(config_path: str | Path) -> Dict[str, dict]:
    config_path = Path(config_path)
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))

    systems = {}
    for name, system in cfg.items():
        brackets_path = config_path.parent / system["brackets_file"]
        lowers, uppers, rates, fees = load_brackets(brackets_path)
        systems[name] = {
            "method": system["method"],
            "standard_deduction": float(system["standard_deduction"]),
            "round_tax": bool(system.get("round_tax", False)),
            "bracket": (lowers, uppers, rates, fees),
        }

    return systems



def calc_tax(bracket, taxable_income: float) -> float:
    #Bracket
    lowers, uppers, rates, fees = bracket

    #Amount of income that lands inside each bracket
    taxable_by_bracket = np.maximum(0.0, np.minimum(taxable_income, uppers)-lowers)

    #Tax from each bracket
    tax_by_bracket = taxable_by_bracket * rates 

    return tax_by_bracket.sum()


def calc_federal_ytd_tax_from_buckets(tax_buckets, std_deduct, ordinary_bracket, ltcg_brackets, ytd_tax: float):
    ordinary_income = tax_buckets.federal_ordinary_income
    pref_income=(
        tax_buckets.federal_ltcg_income
        + tax_buckets.federal_qualified_dividends
    )
    social_security_income = tax_buckets.social_security_income
    tax_exempt_interest = tax_buckets.tax_exempt_interest
    taxable_ss = calc_taxable_social_security(
        ordinary_income=ordinary_income,
        pref_income=pref_income,
        tax_exempt_interest=tax_exempt_interest,
        social_security_income=social_security_income,
        filing_status="single"
    )
    federal_ordinary_income_total = ordinary_income + taxable_ss

    total_income = ordinary_income + pref_income 
    taxable_total = max(0.0, total_income-std_deduct)

    ordinary_taxable_income = max(0.0,federal_ordinary_income_total-std_deduct)
    deduction_left_for_pref= max(0.0, std_deduct-federal_ordinary_income_total)
    pref_taxable_income = max(0.0, pref_income-deduction_left_for_pref)
    ordinary_tax = calc_tax(ordinary_bracket, ordinary_taxable_income)
    pref_tax = calc_ltcg_tax(ordinary_taxable_income, pref_taxable_income, ltcg_brackets)

    new_ytd_tax = ordinary_tax + pref_tax
    
    if np.isnan(ordinary_income):
        raise ValueError(f"ordinary_income is NaN: {ordinary_income}")

    if np.isnan(pref_income):
        raise ValueError(f"pref_income is NaN: {pref_income}")
    
    if np.isnan(ordinary_taxable_income):
        raise ValueError(f"ordinary_taxable_income is NaN: {ordinary_taxable_income}")

    if np.isnan(pref_taxable_income):
        raise ValueError(f"pref_taxable_income is NaN: {pref_taxable_income}")
    
    if np.isnan(ordinary_tax):
        raise ValueError(f"ordinary_tax is NaN: {ordinary_tax}")

    if np.isnan(pref_tax):
        raise ValueError(f"pref_tax is NaN: {pref_tax}")
        
    if np.isnan(new_ytd_tax):
        raise ValueError(
            f"new_ytd_tax is NaN: | ordinary={ordinary_income}, pref={pref_income},"
            f"ordinary_taxable={ordinary_taxable_income}, pref_taxable={pref_taxable_income}"
            )

    new_tax = new_ytd_tax - ytd_tax
    return new_tax, new_ytd_tax

def calc_ltcg_tax(ordinary_taxable_income: float, pref_income: float, ltcg_brackets) -> float:

    if pref_income <= 0:
        return 0.0

    lowers, uppers, rates, fees = ltcg_brackets

    tax = 0.0
    remaining = pref_income

    for lower, upper, rate in zip(lowers, uppers, rates):
        lower = float(lower)
        upper = float(upper)
        rate = float(rate)

        band_start = max(lower, ordinary_taxable_income)
        band_end = max(band_start, upper)

        available_room = max(0.0, band_end-band_start)
        taxed_here = min(remaining, available_room)

        tax += taxed_here * rate
        remaining -= taxed_here

        if remaining <=0:
            break
    return float(tax)

def calc_medicare_ytd_tax(
    medicare_wages_ytd: float,
    prior_ytd_medicare_tax: float,
    filing_status: str = "mfs"
):    
    if filing_status == "mfj":
        addl_threshold = 250000.0
    elif filing_status == "single":
        addl_threshold = 200000.0
    elif filing_status == "mfs":
        addl_threshold = 125000.0
    else:
        raise ValueError(f"Unsupported filing status: {filing_status}")
    
    base_tax = 0.0145 * medicare_wages_ytd
    addl_tax = 0.009 * max(0.0, medicare_wages_ytd-addl_threshold)
    new_ytd_medicare_tax = base_tax + addl_tax
    medicare_tax = new_ytd_medicare_tax - prior_ytd_medicare_tax

    return medicare_tax, new_ytd_medicare_tax

def calc_va_tax(bracket, taxable_income: float) -> float:
    lowers, uppers, rates, fees = bracket

    idx = np.searchsorted(lowers, taxable_income, side="right")-1
    idx = max(idx, 0)

    tax = fees[idx] + rates[idx] * (taxable_income - lowers[idx])

    return tax

def calc_va_ytd_tax(bracket, va_std_deduct: float, ytd_income_real, va_ytd_tax: float):
    new_va_taxable_income = max(0.0, ytd_income_real- va_std_deduct)
    va_new_ytd_tax = calc_va_tax(bracket, new_va_taxable_income)
    va_new_tax = va_new_ytd_tax - va_ytd_tax

    return va_new_tax, va_new_ytd_tax

def calc_taxable_social_security(
    ordinary_income: float,
    pref_income: float,
    tax_exempt_interest: float,
    social_security_income: float,
    filing_status: str = "single"
)-> float:
    if social_security_income <= 0:
        return 0.0
    
    if filing_status == "mfj":
        base1 = 32000.0
        base2 = 44000.0
    elif filing_status == "single":
        base1 = 25000.0
        base2 = 34000.0
    elif filing_status == "mfs":
        base1 = 0.0
        base2 = 0.0
    else:
        raise ValueError(f"Unsupported filing status: {filing_status}")
    
    provisional_income = (ordinary_income + pref_income + tax_exempt_interest + 0.5 * social_security_income)

    if provisional_income <= base1:
        taxable_ss = 0.0
    elif provisional_income <= base2: 
        taxable_ss = min(
            0.5 * social_security_income, 
            0.5 * (provisional_income - base1))
    else:
        taxable_ss = min(
            0.85 * social_security_income,
            0.85 * (provisional_income - base2) + min(0.5 * social_security_income, 0.5 * (base2 - base1))
            
        )
    return max(0.0, taxable_ss)
    

def tax_engine(
    tax_buckets,
    ytd_tax: float,
    va_ytd_tax: float,
    ytd_medicare_tax: float,
    filing_status: str = "mfs",
):
    tax_systems = load_tax_systems("Config/tax_system.json")
    ltcg_brackets = load_brackets("Config/ltcg_brackets.csv")    
    
    # Taxable Social Security
    taxable_ss = calc_taxable_social_security(
        ordinary_income = tax_buckets.federal_ordinary_income,
        pref_income=(tax_buckets.federal_ltcg_income + tax_buckets.federal_qualified_dividends),
        social_security_income = tax_buckets.social_security_income,
        tax_exempt_interest = tax_buckets.tax_exempt_interest,
        filing_status=filing_status,
    )

    #Federal Taxes
    fed_bracket = load_brackets("Config/federal_tax_2025.csv")
    std_deduct = tax_systems["federal"]["standard_deduction"]

    fed_tax_buckets = replace(tax_buckets, federal_ordinary_income=tax_buckets.federal_ordinary_income + taxable_ss)
    
    monthly_tax, new_ytd_tax = calc_federal_ytd_tax_from_buckets(
        fed_tax_buckets, 
        std_deduct, 
        fed_bracket, 
        ltcg_brackets,
        ytd_tax)

     #Medicare Taxes
    medicare_tax, new_ytd_medicare_tax = calc_medicare_ytd_tax(
        medicare_wages_ytd=tax_buckets.payroll_medicare_wages,
        prior_ytd_medicare_tax = ytd_medicare_tax,
        filing_status=filing_status,
     )   

    #Virginia Taxes
    va_bracket = load_brackets("Config/virginia_tax_2025.csv")
    va_std_deduct = tax_systems["virginia"]["standard_deduction"]

    va_monthly_tax, va_new_ytd_tax = calc_va_ytd_tax(
        va_bracket,
        va_std_deduct,
        tax_buckets.va_ordinary_income,
        va_ytd_tax
    )

    return monthly_tax, new_ytd_tax, va_monthly_tax, va_new_ytd_tax, medicare_tax, new_ytd_medicare_tax
    
    