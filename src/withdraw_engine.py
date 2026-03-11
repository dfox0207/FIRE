def classic_withdrawal(m, annual_w0, balances_actuals, withdrawal_start_date, balances, withdrawal_rate, t0, inflation):
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
    return withdrawal, annual_w0, t0

def withdrawal_waterfall(balances, withdrawal, order):
    remaining_withdrawal = withdrawal
    row = balances.copy()
    income_sources = {}
    for acct in order:
        if row[acct] >= remaining_withdrawal:
            row[acct] -= remaining_withdrawal
            income = remaining_withdrawal
            remaining_withdrawal = 0
            break
        else:
            remaining_withdrawal = remaining_withdrawal-row[acct]
            income = row[acct]
            row[acct] = 0
        income_sources[acct] = income      
    balances = row
    return balances, income_sources

def calc_withdrawal(
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
    income_sources = {}
    if m < withdrawal_start_date:
        return balances, income_sources, withdrawal, annual_w0, t0 

    if withdrawal_type== "VPW":
        withdrawal = float(balances.sum())*float(withdrawal_rate)/12.0
                
    elif withdrawal_type == "4pct":
        withdrawal, annual_w0, t0 = classic_withdrawal(m, annual_w0, balances_actuals, withdrawal_start_date, balances, withdrawal_rate, t0, inflation)

    else:
        raise ValueError(f"Unknown withdrawal type: {withdrawal_type}")

    #Take withdrawal from accounts in order
    balances, income_sources = withdrawal_waterfall(balances, withdrawal, order)
        
    return balances, income_sources, withdrawal, annual_w0, t0