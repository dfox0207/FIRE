import numpy as np 





def calc_tax(bracket, taxable_income: float) -> float:
    #Bracket
    lowers, uppers, rates = bracket

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
    lowers, uppers, rates, fee = bracket

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
    std_deduct = 15000.0
    lowers = np.array([0, 11925, 48475, 103350, 197300, 250525, 626350], dtype=float)
    uppers = np.array([11925, 48475, 103350, 197300, 250525, 626350, np.inf], dtype=float)
    rates = np.array([0.10, 0.12, 0.22, 0.24, 0.32, 0.35, 0.37], dtype = float)

    fed_bracket= [lowers, uppers, rates]

    monthly_tax, new_ytd_tax = calc_ytd_tax(
        std_deduct,
        fed_bracket,
        ytd_income_real,
        ytd_tax
    )

    #Virginia Taxes
    va_std_deduct = 8750
    va_lowers = np.array([0,3001, 5001, 17000], dtype=float)
    va_uppers = np.array([3001, 5001, 17000, np.inf], dtype=float)
    va_rates = np.array([0.02,0.03,0.05,0.0575], dtype=float)
    va_fee = np.array([0, 60,120,720], dtype=float) 

    va_bracket = [va_lowers, va_uppers, va_rates, va_fee]

    va_monthly_tax, va_new_ytd_tax = calc_va_ytd_tax(
        va_bracket,
        va_std_deduct,
        ytd_income_real,
        va_ytd_tax
    )

    return monthly_tax, new_ytd_tax, va_monthly_tax, va_new_ytd_tax
    
    