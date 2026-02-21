import pandas as pd
import numpy as np

def projection_engine(start_bal, cf, months, assumptions):
    
    balances = start_bal.copy()
    rows =[]
    withdrawal = 0

    withdrawal_start_date = assumptions["withdrawal_start_date"]
    withdrawal_rate = assumptions["withdrawal_rate"]
    birthday = assumptions["birthday"]
    inflation = assumptions["inflation"]
    basis = assumptions["basis"]

    

    #For each month apply: 
    for m in months:
        #1.apply growth to balances
        balances *= (1+0.10)**(1/12)

        #2.select active cashflows
        active = cf[(cf["start_date"]<=m) & (cf["end_date"].isna() | (cf["end_date"] >= m))]
        flows = active.groupby("account")["monthly_amount"].sum()

        #3. Take Retirement withdrawals
        if m >= withdrawal_start_date:
            withdrawal = balances.sum()*withdrawal_rate/12
            balances = balances.multiply((1-withdrawal_rate)**(1/12))
            


        #4. add cashflows to new balances
        balances = balances.add(flows, fill_value=0)
        
        #5 Calculate Real values
        delta_months = (basis.to_period("M") - m.to_period("M")).n          #months since basis
        balances_real = balances*(1+inflation)**(delta_months/12)
        withdrawal_real = withdrawal*(1+inflation)**(delta_months/12)

        #6 create record row
        row = {"Date": m, **balances.to_dict()}
        
        #7 sum net worth  
        row["Net_Worth"] = balances.sum() 
        row["Withdrawal"] = withdrawal
        row["Age"] = (m-birthday).days / 365.2425
        row["Net_Worth_Real"] = balances_real.sum()
        row["Withdrawal_real"] = withdrawal_real

        #8 append record row
        rows.append(row)

    proj = pd.DataFrame(rows)
    return proj