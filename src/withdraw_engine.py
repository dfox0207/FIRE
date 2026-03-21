import pandas as pd

RMD_ELIGIGIBLE_ACCOUNT_TYPES = {
    "tsp", 
    "457b"
    "403b", 
    "traditional_ira", 
    "401k",
}

def is_rmd_eligible(acct: str, account_tax_map) -> bool:
    account_type = str(account_tax_map.loc[acct, "account_type"]).strip().lower()
    return account_type in RMD_ELIGIGIBLE_ACCOUNT_TYPES

def get_rmd_divisor(age: int, rmd_table: dict[float, float]) -> float | None:
    return rmd_table.get(age)

def calc_annual_rmd(balance: float, divisor: float) -> float:
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

def append_withdrawal_events(*, monthly_events, m, withdrawal_dict):
    for acct, amt in withdrawal_dict.items():
        if amt <=0:
            continue
        add_event(monthly_events, m, f"{acct} Withdrawal", amt, RetirementDistributionIncome(), acct)

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

def calc_withdrawal_optimizer(
    *,
    m,
    balances,
    income_sources,
    monthly_events,
    inflation,
    policy,
    ytd_tax_buckets,
    order,
):

    year = m.year
    policy = policy or {}
    year_policy = policy.get(year, {})


    annual_income_target = year_policy.get("target_annual_net_income_real", 100000.0)
    annual_roth_target = year_policy.get("roth_target_ordinary_income_annual", 0.0)

    monthly_income_target = annual_income_target / 12.0

    current_income_real = sum(income_sources.values())
    required_withdrawal = max(0.0, monthly_income_target - current_income_real)

    current_ordinary_income = 0.0 if ytd_tax_buckets is None else getattr(ytd_tax_buckets, "federal_ordinary_income", 0.0)
    
    month_num = m.month 
    roth_ytd_target = annual_roth_target * month_num/12.0
    roth_conversion = max(0.0, roth_ytd_target - current_ordinary_income)

    balances, withdrawal_dict, total_withdrawn = withdrawal_waterfall(
        balances,
        required_withdrawal + roth_conversion,
        order
    )
    
    actual_withdrawal = 0.0
    remaining_roth = roth_conversion

    for acct, amt in withdrawal_dict.items():
        roth_amt = min(amt, remaining_roth)
        remaining_roth -= roth_amt
        spend_amt = amt - roth_amt
        actual_withdrawal += spend_amt

        if spend_amt > 0:
            income_sources[acct] = income_sources.get(acct, 0.0) + spend_amt
        if roth_amt > 0:
            income_sources["roth_conversion"] = (income_sources.get("roth_conversion", 0.0) + roth_amt)
            balances["ROTH IRA"] += roth_amt
    debug_month = pd.Timestamp("2040-01-01")
    if m == debug_month:
        print("month", m)
        print("annual target", annual_income_target)
        print("monthly target", monthly_income_target)
        print("current_income_real", current_income_real)
        print("required_withdrawal", required_withdrawal)
        print("roth_conversion", roth_conversion)
        print("actual_withdrawal", actual_withdrawal)
        print("income_sources", income_sources)
    

    return balances, income_sources, actual_withdrawal

def withdrawal_waterfall(balances, withdrawal, order, monthly_events=None, m=None):
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

        if monthly_events is not None and m is not None and taken >0:
            add_event(monthly_events, m, f"{acct} Withdrawal", taken, RetirementDistributionIncome(), acct)

    actual_withdrawal = withdrawal - remaining_withdrawal

    balances = row
    return balances, income_sources, actual_withdrawal



def calc_withdrawal(
    *, 
    m,
    rmd_table, 
    account_tax_map,
    age,
    withdrawal_start_date, 
    withdrawal_type, 
    balances, 
    withdrawal_rate, 
    order, 
    inflation, 
    annual_w0=None, 
    t0=None, 
    balances_actuals=None,
    rmd_start_age=73,
    policy=None,
    ytd_tax_buckets=None
    ):
    
    withdrawal = 0.0
    income_sources = {}
    if m < withdrawal_start_date:
        return balances, income_sources, withdrawal, annual_w0, t0 

    if withdrawal_type== "VPW":
        withdrawal = float(balances.sum())*float(withdrawal_rate)/12.0
                
    elif withdrawal_type == "Classic":
        withdrawal, annual_w0, t0 = classic_withdrawal(m, annual_w0, balances_actuals, withdrawal_start_date, balances, withdrawal_rate, t0, inflation)

    elif withdrawal_type == "Optimizer":
        balances, income_sources, withdrawal = calc_withdrawal_optimizer(
            m=m, 
            balances=balances, 
            income_sources=income_sources, 
            monthly_events=monthly_events,
            inflation=inflation, 
            policy=policy, 
            ytd_tax_buckets=ytd_tax_buckets or {}, 
            order=order
        )
        
        return balances, income_sources, withdrawal, annual_w0, t0
    else:
        raise ValueError(f"Unknown withdrawal type: {withdrawal_type}")

    #Take withdrawal from accounts in order
    balances, income_sources, actual_withdrawal = withdrawal_waterfall(balances, withdrawal, order, monthly_events, m=m)

    #Calculate RMD
    rmd_by_account = calc_monthly_rmds(
        balances= balances,
        account_tax_map = account_tax_map,
        age = age,
        rmd_table=rmd_table,
        rmd_start_age=rmd_start_age,
    )

    for acct, rmd_amt in rmd_by_account.items():
        already = income_sources.get(acct, 0.0)
        if already >= rmd_amt:
            continue

        extra = rmd_amt - already
        
        
    return balances, income_sources, actual_withdrawal, annual_w0, t0