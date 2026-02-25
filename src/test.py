from pathlib import Path
import json
import pandas as pd

scenario_path = Path("Config/test.json")
cfg = json.loads(scenario_path.read_text(encoding="utf-8"))

#2. Convert config values to proper Python types
order= cfg["order"]
balances = cfg["balances"]
print(balances)
print(type(balances))

rows = []
row = balances.copy()
for m in range(8):
    withdrawal = 60
    remaining_withdrawal = withdrawal
    
    for acct in order:
        bal = row[acct]
        if bal <= remaining_withdrawal:
            remaining_withdrawal -= bal
            row[acct] = 0
        elif bal == 0:
            row[acct] = 0
        else:
            row[acct] = bal - remaining_withdrawal
    rows.append(row)

proj = pd.DataFrame(rows)
print(proj) 
