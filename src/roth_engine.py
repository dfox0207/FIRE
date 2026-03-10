import pandas as pd

def calc_roth_conv(balance, annual_return, start_date, end_date):
    
    conv_window = (end_date.to_period("M") - start_date.to_period("M")).n

    if conv_window <= 0:
        return 0.0

    r = (1 + annual_return)**(1/12) - 1
    
    roth_conv = balance *r/(1-(1+r)**(-conv_window))

    return roth_conv 


def convert_to_roth(m, balances, assumptions, roth_state):
    
    start_date = assumptions["retirement"]
    end_date = assumptions["birthday"] + pd.DateOffset(years=75)
    annual_return = assumptions["annual_return"]

    tsp = balances["TSP"]
    if start_date <= m <= end_date:
        if roth_state["monthly_conv"] is None:
            roth_state["monthly_conv"] = calc_roth_conv(
                tsp,
                annual_return,
                start_date,
                end_date
            )

        conv = min(roth_state["monthly_conv"], balances["TSP"])

        balances["TSP"] -= conv
        balances["ROTH IRA"] += conv

        return conv

    return 0.0
    