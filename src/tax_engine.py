import json
from pathlib import Path
from typing import Dict, Tuple

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

    return lowers, uppers, rates, fees


def load_tax_systems(config_path: str | Path) -> Dict[str, dict]:
    config_path = Path(config_path)
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))

    systems = {}
    for name, system in cfg.items():
        lowers, uppers, rates, fees = load_brackets(system["brackets_file"])
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


def calc_ytd_tax(std_deduct, bracket, ytd_income_real: float, ytd_tax: float):
    new_ytd_taxable_income = max(0.0, ytd_income_real - std_deduct)
    new_ytd_tax = calc_tax(bracket, new_ytd_taxable_income)

    new_tax = new_ytd_tax - ytd_tax

    return new_tax, new_ytd_tax

def calc_va_tax(bracket, taxable_income: float) -> float:
    lowers, uppers, rates, fees = bracket

    idx = np.searchsorted(lowers, taxable_income, side="right")-1
    idx = max(idx, 0)

    tax = fees[idx] + rates[idx] * (taxable_income - lowers[idx])

    return tax

def calc_va_ytd_tax(bracket, va_std_deduct: float, ytd_income_real: float, va_ytd_tax: float):
    new_va_taxable_income = max(0.0, ytd_income_real- va_std_deduct)
    va_new_ytd_tax = calc_va_tax(bracket, new_va_taxable_income)
    va_new_tax = va_new_ytd_tax - va_ytd_tax

    return va_new_tax, va_new_ytd_tax

def tax_engine(
    ytd_income_real: float,
    ytd_tax: float,
    va_ytd_tax: float
):
    #Federal Taxes
    monthly_tax, new_ytd_tax = calc_ytd_tax(
        std_deduct,
        fed_bracket,
        ytd_income_real,
        ytd_tax
    )

    #Virginia Taxes
    va_monthly_tax, va_new_ytd_tax = calc_va_ytd_tax(
        va_bracket,
        va_std_deduct,
        ytd_income_real,
        va_ytd_tax
    )

    return monthly_tax, new_ytd_tax, va_monthly_tax, va_new_ytd_tax
    
    