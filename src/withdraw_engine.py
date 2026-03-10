
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