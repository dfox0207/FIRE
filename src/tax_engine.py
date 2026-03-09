import numpy as np 





def calc_tax(bracket, taxable_income: float) -> float:
    #Bracket
    lowers, uppers, rates = bracket

    #Amount of income that lands inside each bracket
    taxable_by_bracket = np.maximum(0.0, np.minimum(taxable_income, uppers)-lowers)

    #Tax from each bracket
    tax_by_bracket = taxable_by_bracket * rates

    return tax_by_bracket.sum()


def calc_ytd_tax(bracket, ytd_income_real: float, ytd_tax: float):
    std_deduct = 15000

    new_ytd_taxable_income = max(0.0, ytd_income_real - std_deduct)
    new_ytd_tax = calc_tax(bracket, new_ytd_taxable_income)

    new_tax = new_ytd_tax - ytd_tax

    return new_tax, new_ytd_tax

def tax_engine(
    ytd_income_real: float,
    ytd_tax: float
):
    lowers = np.array([0, 11925, 48475, 103350, 197300, 250525, 626350], dtype=float)
    uppers = np.array([11925, 48475, 103350, 197300, 250525, 626350, np.inf], dtype=float)
    rates = np.array([0.10, 0.12, 0.22, 0.24, 0.32, 0.35, 0.37], dtype = float)

    fed_bracket= [lowers, uppers, rates]

    monthly_tax, new_ytd_tax = calc_ytd_tax(
        fed_bracket,
        ytd_income_real = ytd_income_real,
        ytd_tax= ytd_tax
    )

    return monthly_tax, new_ytd_tax
    
    