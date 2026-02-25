from pathlib import Path
import json
import pandas as pd

scenario_path = Path("Config/test.json")
cfg = json.loads(scenario_path.read_text(encoding="utf-8"))

#2. Convert config values to proper Python types
order= cfg["order"]
balances = cfg["balances"]


rows = []

for m in range(8):
    withdrawal = 60
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
    
    rows.append(row.copy())
    balances = row

proj = pd.DataFrame(rows)
print(proj) 
