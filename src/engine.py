def project_balance(start_balance: float, monthly_contribution: float, annual_return: float, months: int) -> list[float]:
    """
    Pure function:
    - Inputs: numbers
    - Ouput: list of balances by month
    - No file I/O, no prints, no global constants
    """
    r = (1+ annual_return)**(1/12)-1

    #monthly compounding rate
    balances = [start_balance]
    bal = start_balance

    for m in range(months):
        bal = bal * (1+r)+ monthly_contribution
        balances.append(bal)

    return balances