RMD_ELIGIGIBLE_ACCOUNT_TYPES = {
    "tsp", "403b", "traditional_ira", "401k",
}

def is_rmd_eligible(acct: str, account_tax_map) -> bool:
    account_type = str(account_tax_map.loc[acct, "account_type"]).strip().lower()
    return account_type in RMD_ELIGIGIBLE_ACCOUNT_TYPES

def get_rmd_divisor(age: int, rmd_table: dict[float, float]) -> float | None:
    return rmd_table.get(age)

def calc_annual_rmd(blance: float, divisor: float) -> float:
    if divisor <= 0:
        raise ValueError("RMD divisior must be positive")
    return max(0.0, balance/divisor)

def calc_monthly_rmds(
    balances,
    account_tax_map,
    age: float,
    rmd_table: dict[float, float],
    rmd_start_age: int = 73,
)-> dict[str, float]:
    age_int = int(age)

    if age_int < rmd_start_age:
        return {}
    
    divisor = get_rmd_divisor(age_int, rmd_table)
    if divisor is None:
        return{}
    rmd_by_account = {}
    
    for acct in balances.index:
        if not is_rmd_eligible(acct, account_tax_map):
            continue
        bal = float(balances.get(acct, 0.0))
        if bal <= 0:
            continue

        annual_rmd = calc_annual_rmd(bal, divisor)
        monthly_rmd = annual_rmd / 12.0

        if monthly_rmd > 0:
            rmd_by_account[acct] = monthly_rmd
    return rmd_by_account

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
        if remaining_withdrawal <= 0:
            break
        available = row[acct]

        if available >= remaining_withdrawal:
            taken = remaining_withdrawal
            row[acct] -= taken
            remaining_withdrawal = 0.0
            
        else:
            taken = available
            row[acct] = 0.0
            remaining_withdrawal -= taken
        income_sources[acct] = taken
    actual_withdrawal = withdrawal - remaining_withdrawal

    balances = row
    return balances, income_sources, actual_withdrawal



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
    balances, income_sources, actual_withdrawal = withdrawal_waterfall(balances, withdrawal, order)
        
    return balances, income_sources, actual_withdrawal, annual_w0, t0